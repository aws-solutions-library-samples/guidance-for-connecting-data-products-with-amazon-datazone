import os
import json
from datetime import datetime

import boto3
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

# Constant: Represents the governance account id
G_ACCOUNT_ID = os.getenv('G_ACCOUNT_ID')

# Constant: Represents the governance cross account role name to be used when updating metadata in DynamoDB
G_CROSS_ACCOUNT_ASSUME_ROLE_NAME = os.getenv('G_CROSS_ACCOUNT_ASSUME_ROLE_NAME')

# Constant: Represents the governance DynamoDB table to map producer and consumer secrets
G_C_SECRETS_MAPPING_TABLE_NAME = os.getenv('G_C_SECRETS_MAPPING_TABLE_NAME')

# Constant: Represents the recovery window in days that will be assigned when scheduling secret deletion
RECOVERY_WINDOW_IN_DAYS = os.getenv('RECOVERY_WINDOW_IN_DAYS')

g_cross_account_role_arn = f'arn:aws:iam::{G_ACCOUNT_ID}:role/{G_CROSS_ACCOUNT_ASSUME_ROLE_NAME}'

secrets_manager = boto3.client('secretsmanager')
sts = boto3.client('sts')
sts_session = sts.assume_role(RoleArn=g_cross_account_role_arn, RoleSessionName='p-dynamodb-session')

session_key_id = sts_session['Credentials']['AccessKeyId']
session_access_key = sts_session['Credentials']['SecretAccessKey']
session_token = sts_session['Credentials']['SessionToken']

dynamodb = boto3.client('dynamodb', aws_access_key_id=session_key_id, aws_secret_access_key=session_access_key, aws_session_token=session_token)
dynamodb_serializer = TypeSerializer()
dynamodb_deserializer = TypeDeserializer()

def handler(event, context):
    """ Function handler: Function that will delete a subscription secret by 1/ Scheduling its deletion and 
    2/ Deleting metadata item in the governance DynamoDB table that maps associated producer and consumer secrets.

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details. Not used on function
        DeleteKeepSubscriptionSecretDetails: dict - Dict containing delete / keep subscription details including:
            SecretArn: str - Arn of producer shared subscription secret associated to the local consumer (to be deleted) secret.

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        secret_arn: str - Arn of the deleted secret local to the consumer account
        secret_name: str - Name of the deleted secret local to the consumer account
        secret_deleted: str - 'True' flag to confirm secret deletion
        secret_deletion_date: str - Date of secret deletion
        secret_recovery_window_in_days: str - Secret recovery window in days
    """

    event_details = event['EventDetails']
    delete_keep_subscription_secret_details = event['DeleteKeepSubscriptionSecretDetails']

    shared_subscription_secret_arn = delete_keep_subscription_secret_details['SecretArn']
    secret_association_item = get_secret_association_item(shared_subscription_secret_arn)

    project_secret_name = secret_association_item['secret_name']

    secrets_manager_response = delete_secret(project_secret_name)
    delete_secret_association_item(shared_subscription_secret_arn)
    
    response = {
        'secret_name': secrets_manager_response['Name'],
        'secret_arn': secrets_manager_response['ARN'],
        'secret_deleted': 'true',
        'secret_deletion_date': secrets_manager_response['DeletionDate'],
        'secret_recovery_window_in_days': RECOVERY_WINDOW_IN_DAYS
    }

    return response


def get_secret_association_item(producer_secret_arn):
    """ Complementary function to get item with secret mapping details in respective governance DynamoDB table"""

    dynamodb_response = dynamodb.get_item(
        TableName=G_C_SECRETS_MAPPING_TABLE_NAME,
        Key={ 'datazone_producer_shared_secret_arn': dynamodb_serializer.serialize(producer_secret_arn) }
    )

    secret_association_item = {key: dynamodb_deserializer.deserialize(value) for key, value in dynamodb_response['Item'].items()}
    
    return secret_association_item


def delete_secret_association_item(producer_secret_arn):
    """ Complementary function to delete item with secret mapping details in respective governance DynamoDB table"""

    dynamodb_response = dynamodb.delete_item(
        TableName=G_C_SECRETS_MAPPING_TABLE_NAME,
        Key={ 'datazone_producer_shared_secret_arn': dynamodb_serializer.serialize(producer_secret_arn) }
    )


def delete_secret(secret_name):
    """ Complementary function to schedule deletion of a local secret"""

    secrets_manager_response = secrets_manager.delete_secret(
        SecretId=secret_name,
        RecoveryWindowInDays= int(RECOVERY_WINDOW_IN_DAYS)
    )
    
    secrets_manager_response = json.loads(json.dumps(secrets_manager_response, default=json_datetime_encoder))
    
    return secrets_manager_response 


def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")