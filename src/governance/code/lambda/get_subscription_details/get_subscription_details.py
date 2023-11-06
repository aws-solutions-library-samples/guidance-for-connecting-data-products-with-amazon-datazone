import os
import json
import boto3
from datetime import datetime

datazone = boto3.client('datazone') 

def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")

def handler(event, context):
    """ Function handler: Function that will retrieve subscription's details. 1/ Will retrieve listing metadata from Amazon DataZone
    2/ Will retrieve producer project details from Amazon DataZone 3/ Will retrieve consumer project and environment details from Amazon DataZone
    4/ Will build response base on producer, consumer, listing and asset details.

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details including:
            metadata.domain: str - Id of DataZone domain
            data.asset.listingId: str - Id of the DataZone listing associated to subscription
            data.asset.listingVersion: str - Revision of the DataZone listing associated to subscription
            data.projectId: str - Id of the Amazon DataZone consumer project
            data.subscriptionTarget.environmentId: str - Id of the Amazon DataZone consumer environment

    context: dict - Input context. Not used on function

    Returns
    -------
    subscription_details: dict - Dict with subscription details including:
        DomainId: str - Id of the Amazon DataZone domain.
        ProducerProjectDetails: dict - Dict with producer project details.
            ProjectId: str - Id of the Amazon DataZone producer project
            ProjectName: str - Name of the Amazon DataZone producer project
        ConsumerProjectDetails: dict - Dict with producer project details.
            AccountId: str - Consumer environment AWS account id.
            Region: str - Consumer environment region.
            ProjectId: str - Id of the Amazon DataZone consumer project
            ProjectName: str - Name of the Amazon DataZone consumer project
            EnvironmentId: str - Id of the Amazon DataZone consumer environment
            EnvironmentName: str - Name of the Amazon DataZone consumer environment
            EnvironmentProfileId: str - Id of the Amazon DataZone consumer environment profile
            EnvironmentProfileName: str - Name of the Amazon DataZone consumer environment profile
        ListingDetails: dict - Dict with listing details.
            Id: str - Id of the Amazon DataZone listing
            Name: str - Name of the Amazon DataZone listing
            Revision: str - Revision of the Amazon DataZone listing
        AssetDetails: dict - Dict with data asset details. 
            Id: str - Id of the Amazon DataZone data asset
            Revision: str - Revision of the Amazon DataZone data asset
            Type: str - Type of the Amazon DataZone data asset.
            GlueTableDetails: dict - Dict included when AssetType is 'GlueTableAssetType'. Dict includes glue table details:
                AccountId: str - data asset AWS account id.
                Region: str - data asset region.
                DatabaseName: str - data asset glue database name.
                TableName: str - data asset glue table name.
                TableArn: str - data asset glue table arn.
                SourceClassification: str - data asset glue table source classification
    """

    event_details = event['EventDetails']
    domain_id = event_details['metadata']['domain']
    listing_id = event_details['data']['asset']['listingId']
    listing_revision = event_details['data']['asset']['listingVersion']
    consumer_project_id = event_details['data']['projectId']
    consumer_environment_id = event_details['data']['subscriptionTarget']['environmentId']

    datazone_response = datazone.get_listing(domainIdentifier=domain_id, identifier=listing_id, listingRevision=listing_revision)
    listing_details = datazone_response

    data_asset_details = listing_details['item']['assetListing']
    data_asset_type = data_asset_details['assetType']
    data_asset_forms = json.loads(data_asset_details['forms'])
    producer_project_id = data_asset_details['owningProjectId']

    subscription_details = {
        'DomainId': domain_id,
        'ProducerProjectDetails': get_project_details(domain_id, producer_project_id),
        'ConsumerProjectDetails': {
            **get_project_details(domain_id, consumer_project_id),
            **get_environments_details(domain_id, consumer_environment_id)
        },
        'ListingDetails': {
            'Id': listing_details['id'],
            'Name': listing_details['name'],
            'Revision': listing_details['listingRevision'],
        },
        'AssetDetails': {
            'Type': data_asset_type,
            'Id': data_asset_details['assetId'],
            'Revision': data_asset_details['assetRevision']
        }
    }

    if data_asset_type == 'GlueTableAssetType':
        glue_table_form = data_asset_forms['GlueTableForm']

        subscription_details['AssetDetails']['GlueTableDetails'] = {
            'AccountId': glue_table_form['catalogId'],
            'Region': glue_table_form['region'],
            'DatabaseName': glue_table_form['tableArn'].split('/')[1],
            'TableName': glue_table_form['tableName'],
            'TableArn': glue_table_form['tableArn'],
            'SourceClassification': glue_table_form['sourceClassification']
        }

    return subscription_details


def get_project_details(domain_id, project_id):
    """ Complementary function to get Amazon DataZone project details """
    datazone_response = datazone.get_project(domainIdentifier=domain_id, identifier=project_id)
    project_details = {
        'ProjectId': project_id,
        'ProjectName': datazone_response['name']
    }
    return project_details


def get_environments_details(domain_id, environment_id):
    """ Complementary function to get Amazon DataZone environment details """
    environment_full_details = datazone.get_environment(domainIdentifier=domain_id, identifier=environment_id)

    environment_profile_id = environment_full_details['environmentProfileId']
    environment_full_profile_details = datazone.get_environment_profile(domainIdentifier=domain_id, identifier=environment_profile_id)

    environment_details = {
        'AccountId': environment_full_details['awsAccountId'],
        'Region': environment_full_details['awsAccountRegion'],
        'EnvironmentId': environment_id,
        'EnvironmentName': environment_full_details['name'],
        'EnvironmentProfileId': environment_profile_id,
        'EnvironmentProfileName': environment_full_profile_details['name'],
    }

    return environment_details

