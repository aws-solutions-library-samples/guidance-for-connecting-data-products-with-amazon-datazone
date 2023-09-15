import os
import json
import boto3

from datetime import datetime

# Constant: Represents the recovery window in days that will be assigned when scheduling secret deletion
RECOVERY_WINDOW_IN_DAYS = os.getenv('RECOVERY_WINDOW_IN_DAYS')

secrets_manager = boto3.client('secretsmanager')

def handler(event, context):
    """ Function handler: Function that will delete or keep a subscription secret by 1/ Scheduling its deletion.
    Deletion will depend if project user was deleted previously or not.

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details. Not used on function
        UnsubscriptionDetails: dict - Dict containing un-subscription details including:
            SecretName: str - Name of producer local subscription secret.
            DeleteSecret: str - If subscription user was deleted so that associated secret is deleted as well. 

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        secret_arn: str - Arn of the deleted secret local to the producer account
        secret_name: str - Name of the deleted secret local to the producer account
        secret_deleted: str - 'true' or 'false' depending if secret was deleted or not
        secret_deletion_date: str - Date of secret deletion
        secret_recovery_window_in_days: str - Secret recovery window in days
    """

    event_details = event['EventDetails']
    unsubscription_details = event['RevokeSubscriptionDetails']
    unsubscription_secret_name = unsubscription_details['SecretName']
    unsubscription_delete_secret = unsubscription_details['DeleteSecret']

    if unsubscription_delete_secret:
        secrets_manager_response = delete_secret(unsubscription_secret_name)
    else:
        secrets_manager_response = secrets_manager.describe_secret(
            SecretId= unsubscription_secret_name
        )

    response = {
        'secret_name': secrets_manager_response['Name'],
        'secret_arn': secrets_manager_response['ARN'],
        'secret_deleted': 'true' if unsubscription_delete_secret else 'false',
        'secret_deletion_date': secrets_manager_response['DeletionDate'] if unsubscription_delete_secret else None,
        'secret_recovery_window_in_days': RECOVERY_WINDOW_IN_DAYS if unsubscription_delete_secret else None
    }

    return response
    

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