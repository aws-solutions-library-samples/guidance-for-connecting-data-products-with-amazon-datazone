import os
import json
import uuid
from datetime import datetime

import boto3
from boto3.dynamodb.types import TypeSerializer

# Constant: Represents the governance account id
G_ACCOUNT_ID = os.getenv('G_ACCOUNT_ID')

# Constant: Represents the governance cross account role name to be used when updating metadata in DynamoDB
G_CROSS_ACCOUNT_ASSUME_ROLE_NAME = os.getenv('G_CROSS_ACCOUNT_ASSUME_ROLE_NAME')

# Constant: Represents the governance DynamoDB table to map producer and consumer secrets
G_C_SECRETS_MAPPING_TABLE_NAME = os.getenv('G_C_SECRETS_MAPPING_TABLE_NAME')

# Constant: Represents the alias of the account common kms key
A_COMMON_KEY_ALIAS = os.getenv('A_COMMON_KEY_ALIAS')

# Constant: Represents the account id
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

# Constant: Represents the region
REGION = os.getenv('REGION')

g_cross_account_role_arn = f'arn:aws:iam::{G_ACCOUNT_ID}:role/{G_CROSS_ACCOUNT_ASSUME_ROLE_NAME}'

kms = boto3.client('kms')
secrets_manager = boto3.client('secretsmanager')
sts = boto3.client('sts')
sts_session = sts.assume_role(RoleArn=g_cross_account_role_arn, RoleSessionName='c-dynamodb-session')

session_key_id = sts_session['Credentials']['AccessKeyId']
session_access_key = sts_session['Credentials']['SecretAccessKey']
session_token = sts_session['Credentials']['SessionToken']

dynamodb = boto3.client('dynamodb', aws_access_key_id=session_key_id, aws_secret_access_key=session_access_key, aws_session_token=session_token)
dynamodb_serializer = TypeSerializer()

def handler(event, context):
    """ Function handler: Function that will copy a subscription secret by 1/ Retrieving producer shared secret and copying its content into a new one local to the consumer account and 
    2/ Updating metadata in governance DynamoDB table that maps producer and consumer secrets.

    Parameters
    ----------
    event: dict - Input event dict containing:
        SubscriptionDetails: dict - Dict containing details including:
            ConsumerProjectDetails: dict - Dict containing consumer project details including:
                ProjectId: str - DataZone consumer project id
                EnvironmentId: str - DataZone consumer environment id
        ProducerGrantDetails: dict - Dict containing producer grant details including:
            SecretArn: str - Arn of producer shared subscription secret.

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        secret_arn: str - Arn of the copied secret local to the consumer account
        secret_name: str - Name of the copied secret local to the consumer account
    """
    subscription_details = event['SubscriptionDetails']
    producer_grant_details = event['ProducerGrantDetails']

    domain_id = subscription_details['DomainId']
    consumer_project_details = subscription_details['ConsumerProjectDetails']

    consumer_project_id = consumer_project_details['ProjectId']
    consumer_environment_id = consumer_project_details['EnvironmentId']
    shared_subscription_secret_arn = producer_grant_details['SecretArn']

    secrets_manager_response = secrets_manager.get_secret_value(
        SecretId= shared_subscription_secret_arn
    )

    shared_subscription_secret_value = json.loads(secrets_manager_response['SecretString'])
    
    project_secret_name_suffix = str(uuid.uuid4()).replace('-', '')
    project_secret_name = f'dz-conn-c-{consumer_project_id}-{consumer_environment_id}-{project_secret_name_suffix}'

    secrets_manager_response = create_secret(project_secret_name, shared_subscription_secret_value, consumer_environment_id, consumer_project_id, domain_id)
    project_secret_name = secrets_manager_response['Name']
    project_secret_arn = secrets_manager_response['ARN']
    
    update_secret_association_item(shared_subscription_secret_arn, project_secret_arn, project_secret_name, consumer_environment_id, consumer_project_id, domain_id)
    
    response = {
        'secret_arn': project_secret_name,
        'secret_name': project_secret_arn
    }

    return response


def create_secret(secret_name, secret_value, environment_id, project_id, domain_id ):
    """ Complementary function to create a new secret local to the consumer account and associated to subscribing project"""

    kms_response = kms.describe_key(
        KeyId= f'alias/{A_COMMON_KEY_ALIAS}'
    )
    
    kms_key_arn = kms_response['KeyMetadata']['Arn']
    
    secrets_manager_response = secrets_manager.create_secret(
        Name=secret_name,
        KmsKeyId=kms_key_arn,
        SecretString=json.dumps(secret_value),
        Tags=[
            {
                'Key': 'AmazonDataZoneEnvironment',
                'Value': environment_id
            },
            {
                'Key': 'AmazonDataZoneProject',
                'Value': project_id
            },
            {
                'Key': 'AmazonDataZoneDomain',
                'Value': domain_id
            }
        ]
    )
    
    secrets_manager_response = json.loads(json.dumps(secrets_manager_response, default=json_datetime_encoder))
    
    return secrets_manager_response


def update_secret_association_item(shared_secret_arn, secret_arn, secret_name, environment_id, project_id, domain_id):
    """ Complementary function to update item with secret mapping details in respective governance DynamoDB table"""

    secret_association_item = {
        'shared_secret_arn': shared_secret_arn,
        'secret_arn': secret_arn,
        'secret_name': secret_name,
        'datazone_consumer_environment_id':  environment_id,
        'datazone_consumer_project_id':  project_id,
        'datazone_domain': domain_id,
        'owner_account': ACCOUNT_ID,
        'owner_region': REGION,
        'last_updated': datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }
    
    dynamodb_response = dynamodb.put_item(
        TableName=G_C_SECRETS_MAPPING_TABLE_NAME,
        Item={key: dynamodb_serializer.serialize(value) for key, value in secret_association_item.items()}
    )
    
    return secret_association_item


def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")
