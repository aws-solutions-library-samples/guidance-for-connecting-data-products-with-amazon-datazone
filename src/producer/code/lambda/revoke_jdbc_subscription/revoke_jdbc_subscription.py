import os
import json
import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from datetime import datetime
from urllib.parse import urlparse
import awswrangler as wr

# Constant: Represents the governance account id
G_ACCOUNT_ID = os.getenv('G_ACCOUNT_ID')

# Constant: Represents the governance cross account role name to be used when updating metadata in DynamoDB
G_CROSS_ACCOUNT_ASSUME_ROLE_NAME = os.getenv('G_CROSS_ACCOUNT_ASSUME_ROLE_NAME')

# Constant: Represents the governance DynamoDB table to map producer source connection subscriptions
G_P_SOURCE_SUBSCRIPTIONS_TABLE_NAME = os.getenv('G_P_SOURCE_SUBSCRIPTIONS_TABLE_NAME')

# Constant: Represents the account id
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

g_cross_account_role_arn = f'arn:aws:iam::{G_ACCOUNT_ID}:role/{G_CROSS_ACCOUNT_ASSUME_ROLE_NAME}'

secrets_manager = boto3.client('secretsmanager')

sts = boto3.client('sts')
sts_session = sts.assume_role(RoleArn=g_cross_account_role_arn, RoleSessionName='p-dynamodb-session')

session_key_id = sts_session['Credentials']['AccessKeyId']
session_access_key = sts_session['Credentials']['SecretAccessKey']
session_token = sts_session['Credentials']['SessionToken']

dynamodb = boto3.client('dynamodb', aws_access_key_id=session_key_id, aws_secret_access_key=session_access_key, aws_session_token=session_token)
dynamodb_deserializer = TypeDeserializer()
dynamodb_serializer = TypeSerializer()

def handler(event, context):
    """ Function handler: Function that will revoke the subscription in source database by 1/ Connecting to source database using glue connection secret and details,
    2/ Revoke permissions to specific subscribed asset, also if no subscribed assets for project user left will delete user and 
    3/ Updating metadata in governance DynamoDB table that maps subscriptions to producer source connections. 

    Parameters
    ----------
    event: dict - Input event dict containing:
        SubscriptionDetails: dict - Dict containing details including:
            DomainId: str - DataZone domain id
            ConsumerProjectDetails.ProjectId: str - DataZone project id subscribing to the data asset
            ConsumerProjectDetails.EnvironmentId: str - DataZone environment id subscribing to the data asset
        ConnectionDetails: dict - Dict containing glue connection details including:
            ConnectionArn: str - ARN of the glue connection associated to the subscribed asset.
            ConnectionAssetName: str - Name of the asset on source database mapped to subscribed table in Glue catalog
            ConnectionProperties: dict - Dict with connection properties details including:
                SECRET_ID: str - ARN of the secret with credential used by glue connection to connect to source database
                JDBC_CONNECTION_URL: str - Connection URL to connect to source

    context: dict - Input context. Not used on function

    Returns
    -------
    subscription_item: dict - Dict with source connection subscription item details including:
        glue_connection_arn: str - ARN of the glue connection associated to the subscribed asset
        datazone_consumer_environment_id: str - Id of DataZone environment that was subscribed to the asset
        datazone_consumer_project_id: str - Id of DataZone project that was subscribed to the asset
        datazone_domain_id: str - Id of DataZone domain
        secret_arn: str - ARN of the secret (local to the producer account) that can be used to access the subscribed asset
        secret_name: str - Name of the secret (local to the producer account) that can be used to access the subscribed asset
        data_assets: list - List of data assets on source database that can be accessed through the same subscription secret
        owner_account: str - Id of the account that owns the item
        owner_region: str - Region that owns the item
        last_updated: str - Datetime of last update performed on the item
        delete_secret: bool - If subscription user was deleted so that associated secret is deleted as well on following steps. 
    """

    # Get domain, consumer project and glue connection details
    subscription_details = event['SubscriptionDetails']
    glue_connection_details = event['ConnectionDetails']

    domain_id = subscription_details['DomainId']
    consumer_project_details = subscription_details['ConsumerProjectDetails']
    
    # Get subscription project and stablish user
    consumer_project_id = consumer_project_details['ProjectId']
    consumer_environment_id = consumer_project_details['EnvironmentId']
    subscription_user = f'dz_{consumer_environment_id}'

    # # Get connection elements from glue connection
    glue_connection_arn = glue_connection_details['ConnectionArn']
    glue_connection_secret_arn = glue_connection_details['ConnectionProperties']['SECRET_ID']
    glue_connection_url = urlparse(glue_connection_details['ConnectionProperties']['JDBC_CONNECTION_URL'])

    glue_connection_url_path = urlparse(glue_connection_url.path)
    glue_connection_engine = glue_connection_url_path.scheme
    glue_connection_database_name = glue_connection_url_path.path.replace('/', '')

    # Get data asset name associated to glue connection and subscription
    glue_connection_asset_name = glue_connection_details['ConnectionAssetName']

    # Get subscription record and remove unsubscribed data asset
    subscription_item = get_subscription_item(glue_connection_arn, consumer_environment_id)
    subscription_item['data_assets'].remove(glue_connection_asset_name)
    
    # Stablish connection to source, revoke access to data asset and delete user if no subscribed assets left
    delete_subscription_user_and_secret = False if subscription_item['data_assets'] else True
    source_connection = get_connection(glue_connection_engine, glue_connection_secret_arn, glue_connection_database_name)
    revoke_asset_delete_user(glue_connection_engine, source_connection, subscription_user, glue_connection_asset_name, delete_subscription_user_and_secret)
    
    # Delete or update subscription record in DynamoDB
    if delete_subscription_user_and_secret: delete_subscription_item(glue_connection_arn, consumer_environment_id)
    else:
        subscription_secret_arn = subscription_item['secret_arn']
        subscription_secret_name = subscription_item['secret_name']
        subscription_data_assets = subscription_item['data_assets']
        subscription_item = update_subscription_item(glue_connection_arn, consumer_environment_id, consumer_project_id, domain_id, subscription_secret_arn, subscription_secret_name, subscription_data_assets)
    
    subscription_item['delete_secret'] = delete_subscription_user_and_secret
    
    return subscription_item


def get_subscription_item(glue_connection_arn, consumer_environment_id):
    """ Complementary function to get item with source connection subscription details in respective governance DynamoDB table if existent, else None"""

    dynamodb_response = dynamodb.get_item(
        TableName= G_P_SOURCE_SUBSCRIPTIONS_TABLE_NAME,
        Key= {
            'glue_connection_arn': dynamodb_serializer.serialize(glue_connection_arn),
            'datazone_consumer_environment_id': dynamodb_serializer.serialize(consumer_environment_id)
        }
    )
    
    subscription_item = None
    if 'Item' in dynamodb_response:
        subscription_item = {key: dynamodb_deserializer.deserialize(value) for key, value in dynamodb_response['Item'].items()}
    
    return subscription_item


def delete_subscription_item(glue_connection_arn, consumer_environment_id):
    """ Complementary function to delete item with source connection subscription details in respective governance DynamoDB table"""
    
    dynamodb_response = dynamodb.delete_item(
        TableName=G_P_SOURCE_SUBSCRIPTIONS_TABLE_NAME,
        Key= {
            'glue_connection_arn': dynamodb_serializer.serialize(glue_connection_arn),
            'datazone_consumer_environment_id': dynamodb_serializer.serialize(consumer_environment_id),
        }
    )


def update_subscription_item(glue_connection_arn, consumer_environment_id, consumer_project_id, domain_id, secret_arn, secret_name, data_assets):
    """ Complementary function to update item with source connection subscription details in respective governance DynamoDB table"""

    subscription_item = {
        'glue_connection_arn': glue_connection_arn,
        'datazone_consumer_environment_id':  consumer_environment_id,
        'datazone_consumer_project_id':  consumer_project_id,
        'datazone_domain_id': domain_id,
        'secret_arn': secret_arn,
        'secret_name': secret_name,
        'data_assets': data_assets,
        'owner_account': ACCOUNT_ID,
        'last_updated': datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }
    
    dynamodb_response = dynamodb.put_item(
        TableName=G_P_SOURCE_SUBSCRIPTIONS_TABLE_NAME,
        Item={key: dynamodb_serializer.serialize(value) for key, value in subscription_item.items()}
    )
    
    return subscription_item


def get_connection(engine, secret_arn, database_name):
    """ Complementary function to get a new connection to source database"""
    connection = None
    if engine == 'mysql':
        connection = wr.mysql.connect(
            secret_id= secret_arn,
            dbname= database_name
        )
    elif engine == 'postgresql':
        connection = wr.postgresql.connect(
            secret_id= secret_arn,
            dbname= database_name
        )
    elif engine == 'sqlserver':
        connection = wr.sqlserver.connect(
            secret_id= secret_arn,
            dbname= database_name
        )
    elif engine == 'oracle':
        connection = wr.oracle.connect(
            secret_id= secret_arn,
            dbname= database_name
        )
    
    else: raise Exception("Unsupported Database Engine") 

    return connection


def revoke_asset_delete_user(engine, connection, user, asset_name, delete_user):
    """ Complementary function to revoke permission on subscribing data asset in source database from project user and deleted if not remaining subscription assets under same project user"""
    
    with connection.cursor() as cursor:
        if engine == 'mysql':
            revoke_query = f'REVOKE SELECT ON {asset_name} FROM {user};'
            cursor.execute(revoke_query)
            
            if delete_user:
                delete_user_query = f'DROP USER {user};'
                cursor.execute(delete_user_query)   
        
        elif engine == 'postgresql':
            asset_db, asset_schema, asset_table = asset_name.split('.')
            revoke_query = f'REVOKE SELECT ON {asset_schema}.{asset_table} FROM {user};'
            cursor.execute(revoke_query)
            
            if delete_user:
                revoke_owned_query = f'DROP OWNED BY {user};'
                cursor.execute(revoke_owned_query)
                
                delete_user_query = f'DROP USER {user};'
                cursor.execute(delete_user_query)
        
        elif engine == 'sqlserver':                        
            asset_db, asset_schema, asset_table = asset_name.split('.')
            revoke_query = f'REVOKE SELECT ON {asset_schema}.{asset_table} TO {user};'
            cursor.execute(revoke_query)
            
            if delete_user:                
                delete_user_query = f'DROP USER IF EXISTS {user};'
                cursor.execute(delete_user_query)

                delete_login_query = f'DROP LOGIN {user};'
                cursor.execute(delete_login_query)
        
        elif engine == 'oracle':                        
            asset_db, asset_schema, asset_table = asset_name.split('.')
            revoke_query = f'REVOKE SELECT ON {asset_schema}.{asset_table} FROM {user}'
            cursor.execute(revoke_query)
            
            if delete_user:                
                delete_user_query = f"DECLARE userexist INTEGER; BEGIN SELECT COUNT(*) into userexist FROM dba_users WHERE username=UPPER('{user}'); IF (userexist = 1) THEN EXECUTE IMMEDIATE 'DROP USER {user} CASCADE'; END IF; END;"
                cursor.execute(delete_user_query)

    connection.commit()
    connection.close()


def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")