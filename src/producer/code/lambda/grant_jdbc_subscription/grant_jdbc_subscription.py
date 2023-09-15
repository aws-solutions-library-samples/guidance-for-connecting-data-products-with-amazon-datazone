import os
import json
import uuid
import string
import random
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

# Constant: Represents the alias of the account common kms key
A_COMMON_KEY_ALIAS = os.getenv('A_COMMON_KEY_ALIAS')

# Constant: Represents the account id
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

# Constant: Represents the length of the passwords to be generated
PASSWORD_LENGTH = 17

g_cross_account_role_arn = f'arn:aws:iam::{G_ACCOUNT_ID}:role/{G_CROSS_ACCOUNT_ASSUME_ROLE_NAME}'

secrets_manager = boto3.client('secretsmanager')
kms = boto3.client('kms')

sts = boto3.client('sts')
sts_session = sts.assume_role(RoleArn=g_cross_account_role_arn, RoleSessionName='p-dynamodb-session')

session_key_id = sts_session['Credentials']['AccessKeyId']
session_access_key = sts_session['Credentials']['SecretAccessKey']
session_token = sts_session['Credentials']['SessionToken']

dynamodb = boto3.client('dynamodb', aws_access_key_id=session_key_id, aws_secret_access_key=session_access_key, aws_session_token=session_token)
dynamodb_deserializer = TypeDeserializer()
dynamodb_serializer = TypeSerializer()

def handler(event, context):
    """ Function handler: Function that will grant the subscription in source database by 1/ Connecting to source database using glue connection secret and details,
    2/ Create a new user for subscribing project (if non existent) and add grants to specific subscribed asset, then 3/ create a secret with new credentials (if new user was created)
    or point to the already shared secret associated to the same source connection and 4/ Updating metadata in governance DynamoDB table that maps subscriptions to producer source connections. 

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details including:
            authorizedPrincipals: list - List of dicts containing subscription principals details including:
                id: str - DataZone project id
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
        datazone_consumer_project_id: str - Id of DataZone project that subscribed to the asset
        secret_arn: str - ARN of the secret (local to the producer account) that can be used to access the subscribed asset
        secret_name: str - Name of the secret (local to the producer account) that can be used to access the subscribed asset
        data_assets: list - List of data assets on source database that can be accessed through the same subscription secret
        owner_account: str - Id of the account that owns the item
        last_updated: str - Datetime of last update performed on the item
        new_subscription_secret: str - 'true' or 'false' depending on if subscription secret was newly created or not. 
    """

    # Get subscription event and glue connection details
    event_details = event['EventDetails']
    glue_connection_details = event['ConnectionDetails']
    
    # Get subscription project and stablish user / password if new
    subscription_consumer_project = event_details['authorizedPrincipals'][0]['id']
    subscription_user = subscription_consumer_project.replace('proj-', 'dz')[0:16]
    subscription_password = generate_password()

    # Get connection elements from glue connection
    glue_connection_arn = glue_connection_details['ConnectionArn']
    glue_connection_secret_arn = glue_connection_details['ConnectionProperties']['SECRET_ID']
    glue_connection_url = urlparse(glue_connection_details['ConnectionProperties']['JDBC_CONNECTION_URL'])

    glue_connection_url_path = urlparse(glue_connection_url.path)
    glue_connection_engine = glue_connection_url_path.scheme
    glue_connection_host, glue_connection_port  = glue_connection_url_path.netloc.split(':')
    glue_connection_database_name = glue_connection_url_path.path.replace('/', '')

    # Get data asset name associated to glue connection and subscription
    glue_connection_asset_name = glue_connection_details['ConnectionAssetName']

    # Stablish connection to source, create user and grant access to data asset
    source_connection = get_connection(glue_connection_engine, glue_connection_secret_arn, glue_connection_database_name)
    create_grant_user_asset(glue_connection_engine, source_connection, subscription_user, subscription_password, glue_connection_asset_name)
    
    # Retrieve if existing subscription record in DynamoDB
    new_subscription_secret= 'false'
    subscription_item = get_subscription_item(glue_connection_arn, subscription_consumer_project)
    
    if not subscription_item:
        
        # Create secret with connection details for project subscription
        subscription_secret_name_suffix = str(uuid.uuid4()).replace('-', '')
        subscription_secret_name = f'dz-conn-p-{subscription_consumer_project}-{subscription_secret_name_suffix}'
        subscription_secret_value = {
            'engine': glue_connection_engine,
            'host': glue_connection_host,
            'port': glue_connection_port,
            'db_name': glue_connection_database_name,
            'username': subscription_user,
            'password': subscription_password
        }

        secrets_manager_response = create_secret(subscription_secret_name, subscription_secret_value)
        subscription_secret_arn = secrets_manager_response['ARN']
        subscription_secret_name = secrets_manager_response['Name']
        new_subscription_secret = 'true'
        subscription_data_assets = []

    else:
        subscription_secret_arn = subscription_item['secret_arn']
        subscription_secret_name = subscription_item['secret_name']
        subscription_data_assets = subscription_item['data_assets']

    if glue_connection_asset_name not in subscription_data_assets: subscription_data_assets.append(glue_connection_asset_name)

    # Create or update DynamoDB record with subscription details (connection secret and accessible dat assets)
    subscription_item = update_subscription_item(glue_connection_arn, subscription_consumer_project, subscription_secret_arn, subscription_secret_name, subscription_data_assets)
    subscription_item['new_subscription_secret'] = new_subscription_secret

    return subscription_item


def get_subscription_item(glue_connection_arn, datazone_consumer_project_id):
    """ Complementary function to get item with source connection subscription details in respective governance DynamoDB table if existent, else None"""

    dynamodb_response = dynamodb.get_item(
        TableName= G_P_SOURCE_SUBSCRIPTIONS_TABLE_NAME,
        Key= {
            'glue_connection_arn': dynamodb_serializer.serialize(glue_connection_arn),
            'datazone_consumer_project_id': dynamodb_serializer.serialize(datazone_consumer_project_id)
        }
    )
    
    subscription_item = None
    if 'Item' in dynamodb_response:
        subscription_item = {key: dynamodb_deserializer.deserialize(value) for key, value in dynamodb_response['Item'].items()}
    
    return subscription_item


def update_subscription_item(glue_connection_arn, datazone_consumer_project_id, secret_arn, secret_name, data_assets):
    """ Complementary function to update item with source connection subscription details in respective governance DynamoDB table"""

    subscription_item = {
        'glue_connection_arn': glue_connection_arn,
        'datazone_consumer_project_id':  datazone_consumer_project_id,
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


def create_secret(secret_name, secret_value):
    """ Complementary function to create a new secret local to the producer account"""

    kms_response = kms.describe_key(
        KeyId= f'alias/{A_COMMON_KEY_ALIAS}'
    )
    
    kms_key_arn = kms_response['KeyMetadata']['Arn']
    
    secrets_manager_response = secrets_manager.create_secret(
        Name=secret_name,
        KmsKeyId=kms_key_arn,
        SecretString=json.dumps(secret_value)
    )
    
    secrets_manager_response = json.loads(json.dumps(secrets_manager_response, default=json_datetime_encoder))
    
    return secrets_manager_response


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


def create_grant_user_asset(engine, connection, user, password, asset_name):
    """ Complementary function to create a new user for subscribing project in source database (if non existent) and add grant permissions on subscribing data asset in source database"""

    with connection.cursor() as cursor:
        
        if engine == 'mysql':
            create_user_query = f'CREATE USER IF NOT EXISTS {user} IDENTIFIED BY "{password}";'
            cursor.execute(create_user_query)
            
            grant_query = f'GRANT SELECT ON {asset_name} TO {user};'
            cursor.execute(grant_query)     
        
        elif engine == 'postgresql':            
            create_user_query = f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_user WHERE usename='{user}') THEN CREATE ROLE {user} LOGIN PASSWORD '{password}';END IF;END $$;"
            cursor.execute(create_user_query)
            
            asset_db, asset_schema, asset_table = asset_name.split('.')
            grant_schema_query = f'GRANT USAGE ON SCHEMA {asset_schema} TO {user};'
            cursor.execute(grant_schema_query)
            
            grant_asset_query = f'GRANT SELECT ON {asset_schema}.{asset_table} TO {user};'
            cursor.execute(grant_asset_query)
        
        elif engine == 'sqlserver':            
            create_user_query = f"IF NOT EXISTS (SELECT * FROM master.dbo.syslogins WHERE loginname = '{user}') BEGIN CREATE LOGIN {user} WITH PASSWORD = '{password}'; CREATE USER {user} FOR LOGIN {user}; GRANT VIEW DATABASE STATE TO {user}; GRANT VIEW DEFINITION TO {user}; END;"
            cursor.execute(create_user_query)
            
            asset_db, asset_schema, asset_table = asset_name.split('.')
            grant_schema_query = f'GRANT SELECT ON SCHEMA :: {asset_schema} TO {user};'
            cursor.execute(grant_schema_query)
            
            grant_asset_query = f'GRANT SELECT ON {asset_schema}.{asset_table} TO {user};'
            cursor.execute(grant_asset_query)

        elif engine == 'oracle':            
            create_user_query = f"DECLARE userexist INTEGER; BEGIN SELECT COUNT(*) into userexist FROM dba_users WHERE username=UPPER('{user}'); IF (userexist = 0) THEN EXECUTE IMMEDIATE 'CREATE USER {user} IDENTIFIED BY {password}'; EXECUTE IMMEDIATE 'GRANT CONNECT, CREATE SESSION TO {user}'; END IF; END;"
            print(create_user_query)
            cursor.execute(create_user_query)
            
            asset_db, asset_schema, asset_table = asset_name.split('.')
            grant_asset_query = f'GRANT SELECT ON {asset_schema}.{asset_table} TO {user}'
            print(grant_asset_query)
            cursor.execute(grant_asset_query)

    connection.commit()
    connection.close()


def generate_password():
    ''' Complementary function to generate a random password'''
    special_characters = '#$%&*!'
    characters = string.ascii_lowercase + string.ascii_uppercase + string.digits + special_characters
    password = ''.join(random.sample(characters, PASSWORD_LENGTH - 2))
    return f'p_{password}'
    

def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")