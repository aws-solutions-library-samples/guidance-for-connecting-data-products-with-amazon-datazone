import os
import json
import boto3
from datetime import datetime

# Constant: Represents the default data lake datazone blueprint name
DATA_LAKE_BLUEPRINT_NAME = 'DefaultDataLake'

# Constant: Represents the approved status for a datazone subscription
APPROVED_STATUS = 'APPROVED'

# Constant: Represents the revoked status for a datazone subscription
REVOKED_STATUS = 'REVOKED'

# Constant: Represents the cancelled status for a datazone subscription
CANCELLED_STATUS = 'CANCELLED'

# Constant: Arn of the grant subscription workflow state machine
G_SUBSCRIPTION_GRANT_WORKFLOW_ARN = os.getenv('G_SUBSCRIPTION_GRANT_WORKFLOW_ARN')

# Constant: Arn of the revoke subscription workflow state machine
G_SUBSCRIPTION_REVOKE_WORKFLOW_ARN = os.getenv('G_SUBSCRIPTION_REVOKE_WORKFLOW_ARN')

datazone = boto3.client('datazone')

step_functions = boto3.client('stepfunctions')

def handler(event, context):
    """ Function handler: Function that will start either the subscription grant workflow or the subscription revoke workflow with corresponding
    metadata, depending to triggering event sent to to EventBridge by DataZone.
    1/ Will retrieve listing metadata from Amazon DataZone. 2/ Will retrieve consumer environment list from Amazon DataZone 
    3/ For each environment will retrieve its details as well as its bluebrint details.
    4/ For each environment will start a grant or revoke workflow (with proper event structure and metadata) if the environment is associated to the default data lake blueprint.

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details including:
            metadata.domain: str - Id of DataZone domain
            data.subscribedListing.id: str - Id of the DataZone listing associated to subscription
            data.subscribedListing.version: str - Revision of the DataZone listing associated to subscription
            data.subscribedPrincipal.id: str - Id of the Amazon DataZone consumer project
            data.status: str - Status of the Amazon DataZone subscription

    context: dict - Input context. Not used on function

    Returns
    -------
    start_events: list - List of dicts, one for each event that was sent to start a subscription workflow (grant or revoke). Each dict with structure:
        EventDetails: str - Dict with event details.
            metadata: dict - Dict with event metadata details.
                typeName: str - Name of the DataZone event type associated to a subscription grant / revoke event.
                domain: str - Id of DataZone domain
            data: dict - Dict with event data details.
                projectId: str - Id of the Amazon DataZone consumer project
                asset: dict - Dict with asset details.
                    listingId: str - Id of the Amazon DataZone listing
                    listingVersion: str - Revision of the Amazon DataZone listing
                    typeName: str - Type of the Amazon DataZone listing
                subscriptionTarget: dict - Dict with subscription target details. 
                    environmentId: str - Id of the Amazon DataZone consumer environment
                    Type: str - Type of the Amazon DataZone subscription target.
    """
    print(event)

    event_details = event['EventDetails']
    domain_id = event_details['metadata']['domain']
    listing_id = event_details['data']['subscribedListing']['id']
    listing_revision = event_details['data']['subscribedListing']['version']
    consumer_project_id = event_details['data']['subscribedPrincipal']['id']
    subscription_status = event_details['data']['status']

    listing_details = datazone.get_listing(domainIdentifier=domain_id, identifier=listing_id, listingRevision=listing_revision)
    asset_type = listing_details['item']['assetListing']['assetType']

    datazone_response = datazone.list_environments(domainIdentifier=domain_id, projectIdentifier=consumer_project_id)
    consumer_environments = datazone_response['items']

    start_events = []
    for environment in consumer_environments:
        consumer_environment_id = environment['id']

        environment_details = datazone.get_environment(domainIdentifier=domain_id, identifier=consumer_environment_id)
        environment_blueprint_id = environment_details['environmentBlueprintId']
        
        environment_blueprint_details = datazone.get_environment_blueprint(domainIdentifier=domain_id, identifier=environment_blueprint_id)
        environment_blueprint_name = environment_blueprint_details['name']

        if environment_blueprint_name == DATA_LAKE_BLUEPRINT_NAME:
            
            start_subscription_event = {
                'EventDetails': {
                    "metadata": {
                        "typeName": "SubscriptionGrantEntityType",
                        "domain": domain_id
                    },
                    "data": {
                        "asset": {
                            "listingId": listing_id,
                            "listingVersion": listing_revision,
                            "typeName": asset_type
                        },
                        "projectId": consumer_project_id,
                        "subscriptionTarget": {
                            "environmentId": consumer_environment_id,
                            "typeName": "GlueSubscriptionTargetType"
                        }
                    }
                }
            }

            if subscription_status == APPROVED_STATUS:
                step_functions.start_execution(stateMachineArn=G_SUBSCRIPTION_GRANT_WORKFLOW_ARN, input=json.dumps(start_subscription_event))
            
            elif subscription_status in [CANCELLED_STATUS, REVOKED_STATUS]:
                step_functions.start_execution(stateMachineArn=G_SUBSCRIPTION_REVOKE_WORKFLOW_ARN, input=json.dumps(start_subscription_event))

            start_events.append(start_subscription_event)

    return start_events






