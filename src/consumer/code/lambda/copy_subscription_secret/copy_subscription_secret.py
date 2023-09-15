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
        EventDetails: dict - Dict containing details including:
            authorizedPrincipals: list - List of dicts containing subscription principals details including:
                id: str - DataZone project id
        ShareSubscriptionSecretDetails: dict - Dict containing share subscription details including:
            SecretArn: str - Arn of producer shared subscription secret.

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        secret_arn: str - Arn of the copied secret local to the consumer account
        secret_name: str - Name of the copied secret local to the consumer account
    """

    event_details = event['EventDetails']
    share_subscription_secret_details = event['ShareSubscriptionSecretDetails']

    subscription_consumer_project = event_details['authorizedPrincipals'][0]['id']
    shared_subscription_secret_arn = share_subscription_secret_details['SecretArn']

    secrets_manager_response = secrets_manager.get_secret_value(
        SecretId= shared_subscription_secret_arn
    )

    shared_subscription_secret_value = json.loads(secrets_manager_response['SecretString'])
    
    project_secret_name_suffix = str(uuid.uuid4()).replace('-', '')
    project_secret_name = f'dz-conn-c-{subscription_consumer_project}-{project_secret_name_suffix}'

    secrets_manager_response = create_secret(project_secret_name, shared_subscription_secret_value, subscription_consumer_project)
    project_secret_name = secrets_manager_response['Name']
    project_secret_arn = secrets_manager_response['ARN']
    
    update_secret_association_item(shared_subscription_secret_arn, subscription_consumer_project, project_secret_name, project_secret_arn)
    
    response = {
        'secret_arn': project_secret_name,
        'secret_name': project_secret_arn
    }

    return response


def create_secret(secret_name, secret_value, datazone_project_id):
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
                'Key': 'datazone:projectId',
                'Value': datazone_project_id
            }
        ]
    )
    
    secrets_manager_response = json.loads(json.dumps(secrets_manager_response, default=json_datetime_encoder))
    
    return secrets_manager_response


def update_secret_association_item(producer_secret_arn, consumer_project_id, secret_name, secret_arn):
    """ Complementary function to update item with secret mapping details in respective governance DynamoDB table"""

    secret_association_item = {
        'datazone_producer_shared_secret_arn': producer_secret_arn,
        'datazone_consumer_project_id':  consumer_project_id,
        'secret_name': secret_name,
        'secret_arn': secret_arn,
        'owner_account': ACCOUNT_ID,
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
