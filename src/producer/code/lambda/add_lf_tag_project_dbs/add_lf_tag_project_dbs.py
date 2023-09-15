import os
import json
from datetime import datetime
import boto3

# Constant: Lake Formation tag key to add to project databases in glue catalog
P_LAKEFORMATION_TAG_KEY = os.getenv('P_LAKEFORMATION_TAG_KEY')

# Constant: Lake Formation tag value to add to project databases in glue catalog
P_LAKEFORMATION_TAG_VALUE = os.getenv('P_LAKEFORMATION_TAG_VALUE')

# Constant: Suffixes to identify project databases in glue catalog
PROJECT_DB_NAME_SUFFIXES = ['pub_db', 'sub_db']

lakeformation = boto3.client('lakeformation') 

def handler(event, context):
    """ Function handler: Function that will add custom lake formation tag to all project databases in glue catalog
    to allow access to solution's resources on permission grants.

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details including:
            name: str - Name of the DataZone project.

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        project_db_names: list - List with names of the glue databases that where tagged
        lakeformation_tag_key: str - Key of the tag added to project databases
        lakeformation_tag_value: str - 'Value of the tag added to project databases
    """

    event_details = event['EventDetails']
    project_name = event_details['name']
    project_db_name_prefix = project_name.replace('-', '')

    project_db_names = []
    for project_db_name_suffix in PROJECT_DB_NAME_SUFFIXES:
        
        project_db_name = f'{project_db_name_prefix}_{project_db_name_suffix}'
        
        lakeformation_response = lakeformation.add_lf_tags_to_resource(
            Resource= {
                'Database': {
                    'Name': project_db_name
                }
            },
            LFTags= [
                {
                    'TagKey': P_LAKEFORMATION_TAG_KEY,
                    'TagValues': [P_LAKEFORMATION_TAG_VALUE]
                },
            ]
        )
        
        lakeformation_response = json.loads(json.dumps(lakeformation_response, default=json_datetime_encoder))
        project_db_names.append(project_db_name)

    response = {
        'project_db_names': project_db_names,
        'lakeformation_tag_key': P_LAKEFORMATION_TAG_KEY,
        'lakeformation_tag_value': P_LAKEFORMATION_TAG_VALUE
    }

    return response


def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")