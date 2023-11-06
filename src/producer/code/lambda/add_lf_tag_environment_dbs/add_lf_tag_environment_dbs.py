import os
import json
from datetime import datetime
import boto3

# Constant: Lake Formation tag key to add to environment databases in glue catalog
P_LAKEFORMATION_TAG_KEY = os.getenv('P_LAKEFORMATION_TAG_KEY')

# Constant: Lake Formation tag value to add to environment databases in glue catalog
P_LAKEFORMATION_TAG_VALUE = os.getenv('P_LAKEFORMATION_TAG_VALUE')

# Constant: List of keys pointing to glue databases inside environment resource details
P_ENVIRONMENT_DBS_KEYS = ['glueProducerDBName', 'glueConsumerDBName']

lakeformation = boto3.client('lakeformation')

def handler(event, context):
    """ Function handler: Function that will add custom lake formation tag to all environment databases in glue catalog
    to allow access to solution's resources on permission grants.

    Parameters
    ----------
    event: dict - Input event dict containing:
        EnvironmentDetails: dict - Dict containing environment details including:
            EnvironmentResources: dict - Dict containing environment resource details.

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        environment_db_names: list - List with names of the glue databases that where tagged
        lakeformation_tag_key: str - Key of the tag added to environment databases
        lakeformation_tag_value: str - 'Value of the tag added to environment databases
    """
    environment_details = event['EnvironmentDetails']
    environment_resources = environment_details['EnvironmentResources']

    environment_db_names = []
    for glue_db_key in P_ENVIRONMENT_DBS_KEYS:
        
        if glue_db_key in environment_resources:
            
            glue_db_name = environment_resources[glue_db_key]
            lakeformation_response = lakeformation.add_lf_tags_to_resource(
                Resource= {
                    'Database': {
                        'Name': glue_db_name
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
            environment_db_names.append(glue_db_name)

    response = {
        'environment_db_names': environment_db_names,
        'lakeformation_tag_key': P_LAKEFORMATION_TAG_KEY,
        'lakeformation_tag_value': P_LAKEFORMATION_TAG_VALUE
    }

    return response


def json_datetime_encoder(obj):
    """ Complementary function to transform dict objects delivered by AWS API into JSONs """
    if isinstance(obj, (datetime)): return obj.strftime("%Y-%m-%dT%H:%M:%S")