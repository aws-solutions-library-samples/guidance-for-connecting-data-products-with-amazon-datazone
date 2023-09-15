import os

import boto3

# Constant: Represents the name of the inline policy to be removed from project roles
A_PROJECT_LAMBDA_INLINE_POLICY_NAME = os.getenv('A_PROJECT_LAMBDA_INLINE_POLICY_NAME')

# Constant: Represents the account id
A_ACCOUNT_ID = os.getenv('A_ACCOUNT_ID')

# Constant: Represents the arn of the default DataZone permission boundary to restore on project roles
DEFAULT_DATAZONE_PERMISSION_BOUNDARY_ARN = 'arn:aws:iam::aws:policy/AmazonDataZoneProjectRolePermissionsBoundary'

# Constant: Represents the arn of the AWS managed policy that allows usage of service catalog and will be removed from project roles
SERVICE_CATALOG_POLICY_ARN = 'arn:aws:iam::aws:policy/AWSServiceCatalogEndUserFullAccess'

# Constant: Represents a list of prefixes used by DataZone when creating project roles.
PROJECT_ROLE_PREFIXES = ['datazone-usr-c', 'datazone-usr-o', 'datazone-usr-v']

iam = boto3.client('iam')

def handler(event, context):
    """ Function handler: Function that will clean project roles by 1/ Replacing permission boundary with default one assigned by Amazon DataZone,
    2/ Remove inline policy that extended project role permissions and 3/ Remove additional attached policies that were not assigned originally by Amazon DataZone

    Parameters
    ----------
    event: dict - Input event dict containing:
        EventDetails: dict - Dict containing details including:
            projectAccount: str - Id of account owning the DataZone project
            projectId: str - Id of DataZone project
            name: str - Name of DataZone project

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        project_role_arns: list - List containing cleaned project role arns (str) 
    """
     
    event_details = event['EventDetails']
    project_account = event_details['projectAccount']
    project_id = event_details['projectId']
    project_name = event_details['name']

    project_role_arns = []
    for project_role_prefix in PROJECT_ROLE_PREFIXES:
        
        project_role_name = f'{project_role_prefix}-{project_id}'
        
        iam.put_role_permissions_boundary(
            RoleName= project_role_name,
            PermissionsBoundary= DEFAULT_DATAZONE_PERMISSION_BOUNDARY_ARN
        )
        
        try:
            iam.delete_role_policy(
                RoleName= project_role_name,
                PolicyName= A_PROJECT_LAMBDA_INLINE_POLICY_NAME,
            )

            iam.detach_role_policy(
                RoleName= project_role_name,
                PolicyArn= SERVICE_CATALOG_POLICY_ARN
            )
            
        except: pass

        project_role_arn = f'arn:aws:iam::{A_ACCOUNT_ID}:role/{project_role_name}'
        project_role_arns.append(project_role_arn)

    response = {
        'project_role_arns': project_role_arns
    }

    return response

