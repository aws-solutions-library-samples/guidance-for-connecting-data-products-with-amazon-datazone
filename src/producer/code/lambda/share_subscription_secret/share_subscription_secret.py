import json
import boto3
import os

# Constant: Represents the account id
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

# Constant: Name of the role in consumer account that will be able to retrieve shared secret
C_ROLE_NAME = os.getenv('C_ROLE_NAME')

secrets_manager = boto3.client('secretsmanager')

def handler(event, context):
    """ Function handler: Function that will share subscription secret by 1/ Adding a resource policy that allows access by consumer environment account (specific target role)
    when secret is new. When is an already shared secret it won't do anything.

    Parameters
    ----------
    event: dict - Input event dict containing:
        SubscriptionDetails: dict - Dict containing details including:
            ConsumerProjectDetails.AccountId: str - Account id of the DataZone environment subscribing to the data asset
        GrantSubscriptionDetails: dict - Dict containing grant subscription details including:
            SecretName: str - Name of subscription secret to be shared.
            NewSubscriptionSecret: bool - If subscription secret was newly created or not (reused and already shared).

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        secret_arn: str - Arn of the copied secret local to the consumer account
        secret_name: str - Name of the copied secret local to the consumer account
        new_subscription_secret: bool - If subscription secret was newly created or not (reused and already shared).
        subscription_consumer_role: str - ARN of the role that can access the secret on the consumer account
    """
    subscription_details = event['SubscriptionDetails']
    grant_subscription_details = event['GrantSubscriptionDetails']
    
    consumer_project_details = subscription_details['ConsumerProjectDetails']
    consumer_account_id = consumer_project_details['AccountId']
    subscription_consumer_roles = [f'arn:aws:iam::{consumer_account_id}:role/{C_ROLE_NAME}']

    subscription_secret_name = grant_subscription_details['SecretName']
    new_subscription_secret = grant_subscription_details['NewSubscriptionSecret']
        
    subscription_secret_resource_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"
                },
                "Action": "secretsmanager:*",
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": subscription_consumer_roles
                },
                "Action": "secretsmanager:GetSecretValue",
                "Resource": "*"
            }
        ]
    }

    secrets_manager_response = secrets_manager.put_resource_policy(
        SecretId= subscription_secret_name,
        ResourcePolicy= json.dumps(subscription_secret_resource_policy)
    )

    response = {
        'secret_name': secrets_manager_response['Name'],
        'secret_arn': secrets_manager_response['ARN'],
        'new_subscription_secret': new_subscription_secret,
        'subscription_consumer_roles': subscription_consumer_roles
    }

    return response
