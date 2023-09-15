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
        EventDetails: dict - Dict containing details including:
            authorizedPrincipals: list - List of dicts containing subscription principals details including:
                id: str - DataZone project id
            dataAssetName: str - Name of the data asset that consumer is subscribing to

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details:
        datazone_consumer_project_id: str - Id of DataZone project that subscribed to the asset
        datazone_asset_name: str - Name of the asset that the consumer project was subscribed to.
    """
    
    event_details = event['EventDetails']

    subscription_consumer_project = event_details['authorizedPrincipals'][0]['id']
    subscription_asset_name = event_details['dataAssetName']
    
    delete_asset_subscription_item(subscription_consumer_project, subscription_asset_name)

    response = {
        'datazone_consumer_project_id': subscription_consumer_project,
        'datazone_asset_name': subscription_asset_name
    }

    return response


def delete_asset_subscription_item(consumer_project_id, asset_name):
    """ Complementary function to delete item with asset subscription details in respective governance DynamoDB table"""

    dynamodb_response = dynamodb.delete_item(
        TableName=G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME,
        Key={
            'datazone_consumer_project_id': dynamodb_serializer.serialize(consumer_project_id),
            'datazone_asset_name': dynamodb_serializer.serialize(asset_name)
        }
    )


def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")