import os
from datetime import datetime

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

# Constant: Represents the governance account id
G_ACCOUNT_ID = os.getenv('G_ACCOUNT_ID')

# Constant: Represents the governance cross account role name to be used when updating metadata in DynamoDB
G_CROSS_ACCOUNT_ASSUME_ROLE_NAME = os.getenv('G_CROSS_ACCOUNT_ASSUME_ROLE_NAME')

# Constant: Represents the governance DynamoDB table to map producer and consumer secrets
G_C_SECRETS_MAPPING_TABLE_NAME = os.getenv('G_C_SECRETS_MAPPING_TABLE_NAME')

# Constant: Represents the governance DynamoDB table to track consumer subscriptions (assets)
G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME = os.getenv('G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME')

# Constant: Represents the account id
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

g_cross_account_role_arn = f'arn:aws:iam::{G_ACCOUNT_ID}:role/{G_CROSS_ACCOUNT_ASSUME_ROLE_NAME}'

sts = boto3.client('sts')
sts_session = sts.assume_role(RoleArn=g_cross_account_role_arn, RoleSessionName='p-dynamodb-session')

session_key_id = sts_session['Credentials']['AccessKeyId']
session_access_key = sts_session['Credentials']['SecretAccessKey']
session_token = sts_session['Credentials']['SessionToken']

dynamodb = boto3.client('dynamodb', aws_access_key_id=session_key_id, aws_secret_access_key=session_access_key, aws_session_token=session_token)
dynamodb_deserializer = TypeDeserializer()
dynamodb_serializer = TypeSerializer()

def handler(event, context):
    """ Function handler: Function that will update subscription asset metadata in governance DynamoDB table

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details including:
            dataAssetName: str - Name of the data asset that consumer is subscribing to
        ShareSubscriptionSecretDetails: dict - Dict containing share subscription details including:
            SecretArn: str - Arn of producer shared subscription secret.

    context: dict - Input context. Not used on function

    Returns
    -------
    asset_subscription_item: dict - Dict with asset subscription item details:
        datazone_consumer_project_id: str - Id of DataZone project that subscribed to the asset
        datazone_asset_name: str - Name of the asset that the consumer project subscribed to.
        secret_name: str - Name of the secret (local to the consumer account) that can be used to access the subscribed asset
        secret_arn: str - ARN of the secret (local to the consumer account) that can be used to access the subscribed asset
        owner_account: str - Id of the account that owns the item
        last_updated: str - Datetime of last update performed on the item
    """

    event_details = event['EventDetails']
    share_subscription_secret_details = event['ShareSubscriptionSecretDetails']

    shared_subscription_secret_arn = share_subscription_secret_details['SecretArn']
    secret_association_item = get_secret_association_item(shared_subscription_secret_arn)
    subscription_consumer_project = secret_association_item['datazone_consumer_project_id']
    subscription_secret_name = secret_association_item['secret_name']
    subscription_secret_arn = secret_association_item['secret_arn']

    subscription_asset_name = event_details['dataAssetName']
    asset_subscription_item = update_asset_subscription_item(subscription_consumer_project, subscription_asset_name, subscription_secret_name, subscription_secret_arn)

    return asset_subscription_item


def get_secret_association_item(producer_secret_arn):
    """ Complementary function to get item with secret mapping details in respective governance DynamoDB table"""

    dynamodb_response = dynamodb.get_item(
        TableName= G_C_SECRETS_MAPPING_TABLE_NAME,
        Key= {
            'datazone_producer_shared_secret_arn': dynamodb_serializer.serialize(producer_secret_arn)
        }
    )
    
    secret_association_item = None
    if 'Item' in dynamodb_response:
        secret_association_item = {key: dynamodb_deserializer.deserialize(value) for key, value in dynamodb_response['Item'].items()}
    
    return secret_association_item


def update_asset_subscription_item(consumer_project_id, asset_name, secret_name, secret_arn):
    """ Complementary function to update item with asset subscription details in respective governance DynamoDB table"""

    asset_subscription_item = {
        'datazone_consumer_project_id': consumer_project_id,
        'datazone_asset_name':  asset_name,
        'secret_name': secret_name,
        'secret_arn': secret_arn,
        'owner_account': ACCOUNT_ID,
        'last_updated': datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }
    
    dynamodb_response = dynamodb.put_item(
        TableName=G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME,
        Item={key: dynamodb_serializer.serialize(value) for key, value in asset_subscription_item.items()}
    )
    
    return asset_subscription_item


def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")
