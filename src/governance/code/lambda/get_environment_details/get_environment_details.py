import os
import json
import boto3
from datetime import datetime

datazone = boto3.client('datazone') 

def handler(event, context):
    """ Function handler: Function that will retrieve environment's details. 1/ Will retrieve environment metadata from Amazon DataZone, then
    2/ will retrieve environment blueprint metadata from Amazon DataZone.

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details including:
            metadata.domain: str - Id of DataZone domain
            data.environmentId: str - Id of DataZone environment

    context: dict - Input context. Not used on function

    Returns
    -------
    environment_details: dict - Dict with Amazon DataZone environment details:
        AccountId: Id of the AWS account hosting the environment
        Region: Region hosting the environment
        DomainId: Id of the Amazon DataZone domain
        ProjectId: Id of the Amazon DataZone project owning the environment
        EnvironmentId: str - Id of the Amazon DataZone environment.
        EnvironmentName: str - Name of the Amazon DataZone environment.
        EnvironmentBlueprintId: str - Id of the Amazon DataZone environment blueprint.
        EnvironmentBlueprintName: str - Name of the Amazon DataZone environment blueprint.
        EnvironmentResources: dict - Dictionary with all provisioned resources for Amazon DataZone environment
    """

    event_details = event['EventDetails']
    
    domain_id = event_details['metadata']['domain']
    environment_id = event_details['data']['environmentId']
    delete_status_overwrite = True if 'delete' in event_details['data'] else False

    datazone_response = datazone.get_environment(domainIdentifier=domain_id, identifier=environment_id)
    account_id = datazone_response['awsAccountId']
    region = datazone_response['awsAccountRegion']
    project_id = datazone_response['projectId']
    environment_name = datazone_response['name']
    environment_status = datazone_response['status'] if not delete_status_overwrite else 'DELETING'
    environment_blueprint_id = datazone_response['environmentBlueprintId']

    environment_resources = {}
    if 'provisionedResources' in datazone_response:
        environment_resources = {
            resource['name']: resource['value'] for resource in datazone_response['provisionedResources']
        }

    datazone_response = datazone.get_environment_blueprint(domainIdentifier=domain_id, identifier=environment_blueprint_id)
    environment_blueprint_name = datazone_response['name']

    environment_details = {
        'AccountId': account_id,
        'Region': region,
        'DomainId': domain_id,
        'ProjectId': project_id,
        'EnvironmentId': environment_id,
        'EnvironmentName': environment_name,
        'EnvironmentStatus': environment_status,
        'EnvironmentBlueprintId': environment_blueprint_id,
        'EnvironmentBlueprintName': environment_blueprint_name,
        'EnvironmentResources': environment_resources
    }

    return environment_details

def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")
