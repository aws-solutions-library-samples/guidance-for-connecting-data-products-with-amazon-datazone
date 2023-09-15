import os
import json
import boto3
from datetime import datetime

# Constant: Represents the account id
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

# Constant: Represents the region
REGION = os.getenv('REGION')

glue = boto3.client('glue') 

def handler(event, context):
    """ Function handler: Function that will retrieve subscription's data asset source glue connection details. 1/ Will retrieve data asset metadata from glue data catalog, then
    2/ will retrieve connection details, including credentials secret name/arn and source data asset name

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details including:
            sourceDatabaseName: str - Name of the glue data catalog source database where subscribed asset is located
            sourceTableName: str - Name of the table in the glue catalog that the subscription is pointing to

    context: dict - Input context. Not used on function

    Returns
    -------
    glue_connection_details: dict - Dict with glue connection details:
        ConnectionType: str - Type of the glue connection associated to the subscribed asset.
        ConnectionArn: str - ARN of the glue connection associated to the subscribed asset.
        ConnectionName: str - Name of the glue connection associated to the subscribed asset.
        ConnectionProperties: dict - Dict with connection properties details including:
             JDBC_ENFORCE_SSL: str - 'True' or 'False' depending if SSL is enforced by connection
             JDBC_CONNECTION_URL: str - Connection URL to connect to source
             SECRET_ID: str - ARN of the secret with credential used by glue connection to connect to source database
        ConnectionAssetName: str - Name of the asset on source database mapped to subscribed table in Glue catalog
        ConnectionCrawlerName: str - Name of the crawler the retrieved subscribed asset
    """

    event_details = event['EventDetails']
    
    glue_database_name = event_details['sourceDatabaseName']
    glue_table_name = event_details['sourceTableName']

    glue_response = glue.get_table(
        DatabaseName=glue_database_name,
        Name=glue_table_name
    )

    glue_response = json.loads(json.dumps(glue_response, default=json_datetime_encoder))
    glue_table_details = glue_response['Table']
    glue_table_database_asset_name = glue_table_details['StorageDescriptor']['Location']
    glue_crawler_name = glue_table_details['Parameters']['UPDATED_BY_CRAWLER']
    glue_connection_name = glue_table_details['Parameters']['connectionName']
    glue_connection_arn = f'arn:aws:glue:{REGION}:{ACCOUNT_ID}:connection/{glue_connection_name}'

    glue_response = glue.get_connection(
        Name=glue_connection_name
    )

    glue_response = json.loads(json.dumps(glue_response, default=json_datetime_encoder))
    glue_connection_type = glue_response['Connection']['ConnectionType']
    glue_connection_properties = glue_response['Connection']['ConnectionProperties']

    glue_connection_details = {
        'ConnectionType': glue_connection_type,
        'ConnectionArn': glue_connection_arn,
        'ConnectionName': glue_connection_name,
        'ConnectionProperties': glue_connection_properties,
        'ConnectionAssetName': glue_table_database_asset_name,
        'ConnectionCrawlerName': glue_crawler_name
    }

    return glue_connection_details


def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")