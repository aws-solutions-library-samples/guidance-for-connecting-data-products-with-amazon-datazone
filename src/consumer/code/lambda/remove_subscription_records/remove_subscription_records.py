import os
from datetime import datetime

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

# Constant: Represents the governance account id
G_ACCOUNT_ID = os.getenv('G_ACCOUNT_ID')

# Constant: Represents the governance cross account role name to be used when updating metadata in DynamoDB
G_CROSS_ACCOUNT_ASSUME_ROLE_NAME = os.getenv('G_CROSS_ACCOUNT_ASSUME_ROLE_NAME')

# Constant: Represents the governance DynamoDB table to track consumer subscriptions (assets)
G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME = os.getenv('G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME')

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
    """ Function handler: Function that will delete subscription asset metadata in governance DynamoDB table

    Parameters
    ----------
    event: dict - Input event dict containing:
        SubscriptionDetails: dict - Dict containing subscription details including:
            ConsumerProjectDetails: dict - Dict containing consumer details including:
                EnvironmentId: str - Id of the DataZone consumer environment
            AssetDetails: dict - Dict containing asset details including:
                Id: str - Id of the data asset that consumer is subscribing to

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details:
        datazone_consumer_environment_id: str - Id of DataZone environment that subscribed to the asset
        datazone_consumer_project_id: str - Id of DataZone project that subscribed to the asset
        datazone_domain_id: str - Id of DataZone domain
        datazone_asset_id: str - Id of the asset that the consumer subscribed to.
        datazone_asset_revision: str - Revision of the asset that the consumer subscribed to.
        datazone_asset_type: str - Type of the asset that the consumer subscribed to.
        datazone_listing_id: str - Id of the listing associated to the asset that the consumer subscribed to.
        datazone_listing_revision: str - Revision of the listing associated to the asset that the consumer subscribed to.
        datazone_listing_name: str - Name of the listing associated to the asset that the consumer subscribed to.
        secret_arn: str - ARN of the secret (local to the consumer account) that can be used to access the subscribed asset
        secret_name: str - Name of the secret (local to the consumer account) that can be used to access the subscribed asset
        owner_account: str - Id of the account that owns the item
        owner_region: str - Region that owns the item
        last_updated: str - Datetime of last update performed on the item
    """
    subscription_details = event['SubscriptionDetails']
    
    consumer_project_details = subscription_details['ConsumerProjectDetails']
    consumer_asset_details = subscription_details['AssetDetails']
    
    environment_id = consumer_project_details['EnvironmentId']
    asset_id = consumer_asset_details['Id']
    
    asset_subscription_item = get_asset_subscription_item(environment_id, asset_id)
    delete_asset_subscription_item(environment_id, asset_id)

    return asset_subscription_item


def get_asset_subscription_item(environment_id, asset_id):
    """ Complementary function to get item with asset subscription details from respective governance DynamoDB table """

    dynamodb_response = dynamodb.get_item(
        TableName=G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME,
        Key={ 
            'datazone_consumer_environment_id': dynamodb_serializer.serialize(environment_id),
            'datazone_asset_id': dynamodb_serializer.serialize(asset_id)
        }
    )

    asset_subscription_item = {key: dynamodb_deserializer.deserialize(value) for key, value in dynamodb_response['Item'].items()}
    
    return asset_subscription_item


def delete_asset_subscription_item(environment_id, asset_id):
    """ Complementary function to delete item with asset subscription details in respective governance DynamoDB table"""

    dynamodb_response = dynamodb.delete_item(
        TableName=G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME,
        Key={
            'datazone_consumer_environment_id': dynamodb_serializer.serialize(environment_id),
            'datazone_asset_id': dynamodb_serializer.serialize(asset_id)
        }
    )


def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")