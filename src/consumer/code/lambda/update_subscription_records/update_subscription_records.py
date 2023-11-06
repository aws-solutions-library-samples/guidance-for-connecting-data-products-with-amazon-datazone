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

# Constant: Represents the region
REGION = os.getenv('REGION')

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
        SubscriptionDetails: dict - Dict containing subscription details including:
            DomainId: str - DataZone domain id
            ConsumerProjectDetails: dict - Dict containing consumer details including:
                ProjectId: str - DataZone consumer project id
                EnvironmentId: str - DataZone consumer environment id
            AssetDetails: dict - Dict containing asset details including:
                Id: str - Id of the data asset that consumer is subscribing to
                Revision: str - Revision of the data asset that consumer is subscribing to
                Type: str - Type of the data asset that consumer is subscribing to
            ListingDetails: dict - Dict containing listing details including:
                Id: str - Id of the listing associated to the data asset that consumer is subscribing to
                Revision: str - Revision of the listing associated to the data asset that consumer is subscribing to
                Name: str - Name of the listing associated to the data asset that consumer is subscribing to
        ProducerGrantDetails: dict - Dict containing producer grant details including:
            SecretArn: str - Arn of producer shared subscription secret.

    context: dict - Input context. Not used on function

    Returns
    -------
    asset_subscription_item: dict - Dict with asset subscription item details:
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
    producer_grant_details = event['ProducerGrantDetails']

    domain_id = subscription_details['DomainId']
    consumer_project_details = subscription_details['ConsumerProjectDetails']
    asset_details = subscription_details['AssetDetails']
    listing_details = subscription_details['ListingDetails']

    consumer_environment_id = consumer_project_details['EnvironmentId']
    consumer_project_id = consumer_project_details['ProjectId']
    asset_id = asset_details['Id']
    asset_revision = asset_details['Revision']
    asset_type = asset_details['Type']
    listing_id = listing_details['Id']
    listing_revision = listing_details['Revision']
    listing_name = listing_details['Name']

    shared_secret_arn = producer_grant_details['SecretArn']
    secret_association_item = get_secret_association_item(shared_secret_arn)
    secret_arn = secret_association_item['secret_arn']
    secret_name = secret_association_item['secret_name']

    asset_subscription_item = update_asset_subscription_item(
        consumer_environment_id, consumer_project_id, domain_id, asset_id, asset_revision, asset_type,
        listing_id, listing_revision, listing_name, secret_arn, secret_name
    )

    return asset_subscription_item


def get_secret_association_item(shared_secret_arn):
    """ Complementary function to get item with secret mapping details in respective governance DynamoDB table"""

    dynamodb_response = dynamodb.get_item(
        TableName= G_C_SECRETS_MAPPING_TABLE_NAME,
        Key= { 'shared_secret_arn': dynamodb_serializer.serialize(shared_secret_arn) }
    )
    
    secret_association_item = None
    if 'Item' in dynamodb_response:
        secret_association_item = {key: dynamodb_deserializer.deserialize(value) for key, value in dynamodb_response['Item'].items()}
    
    return secret_association_item


def update_asset_subscription_item(environment_id, project_id, domain_id, asset_id, asset_revision, asset_type, listing_id, listing_revision, listing_name, secret_arn, secret_name):
    """ Complementary function to update item with asset subscription details in respective governance DynamoDB table"""

    asset_subscription_item = {
        'datazone_consumer_environment_id': environment_id,
        'datazone_consumer_project_id': project_id,
        'datazone_domain_id': domain_id,
        'datazone_asset_id':  asset_id,
        'datazone_asset_revision':  asset_revision,
        'datazone_asset_type':  asset_type,
        'datazone_listing_id':  listing_id,
        'datazone_listing_revision':  listing_revision,
        'datazone_listing_name':  listing_name,
        'secret_arn': secret_arn,
        'secret_name': secret_name,
        'owner_account': ACCOUNT_ID,
        'owner_region': REGION,
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
