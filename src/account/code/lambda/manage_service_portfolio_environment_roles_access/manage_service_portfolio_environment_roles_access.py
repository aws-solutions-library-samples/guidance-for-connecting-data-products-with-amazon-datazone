import os
import json

import boto3

# Constant: Represents the service portfolio id that will be shared to DataZone project roles
A_SERVICE_PORTFOLIO_ID = os.getenv('A_SERVICE_PORTFOLIO_ID')

# Constant: Represents the resource id to be returned to CDK on request.
PHYSICAL_RESOURCE_ID = 'dz-conn-a-project-roles-access'

# Constant: Represents a pattern string that identifies any DataZone project role.
PROJECT_ROLES_ARN_PATTERN = 'arn:aws:iam:::role/datazone_usr_*'

servicecatalog = boto3.client('servicecatalog')

def handler(event, context):
    """ Function handler: Function that will be triggered by CDK when deploying or deleting account common stack.
    Function will associate or disassociate all DataZone project roles from account service catalog portfolio.

    Parameters
    ----------
    event: dict - Input event dict containing:
        RequestType: str - Type of event invoking the function from CDK

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        PhysicalResourceId: str - Physical resource id required by CDK
    """

    request_type = event['RequestType'].lower()
    
    if request_type == 'create':
        return on_update(event)
    
    if request_type == 'update':
        return on_update(event)
    
    if request_type == 'delete':
        return on_delete(event)
    
    raise Exception(f'Invalid request type: {request_type}')


def on_update(event):
    """ Complementary function to associate (on CDK update event) all DataZone projects roles to service catalog portfolio"""

    servicecatalog_response = servicecatalog.associate_principal_with_portfolio(
        PortfolioId= A_SERVICE_PORTFOLIO_ID,
        PrincipalARN= PROJECT_ROLES_ARN_PATTERN,
        PrincipalType= 'IAM_PATTERN'
    )

    print(json.dumps(servicecatalog_response, indent=2))

    return {'PhysicalResourceId': PHYSICAL_RESOURCE_ID}


def on_delete(event):
    """ Complementary function to disassociate (on CDK delete event) all DataZone projects roles from service catalog portfolio"""

    servicecatalog_response = servicecatalog.disassociate_principal_from_portfolio(
        PortfolioId= A_SERVICE_PORTFOLIO_ID,
        PrincipalARN= PROJECT_ROLES_ARN_PATTERN,
        PrincipalType= 'IAM_PATTERN'
    )

    print(json.dumps(servicecatalog_response, indent=2))

    return {'PhysicalResourceId': PHYSICAL_RESOURCE_ID}
