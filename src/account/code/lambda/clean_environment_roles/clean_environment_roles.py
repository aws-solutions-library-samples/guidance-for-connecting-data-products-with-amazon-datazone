import os

import boto3

# Constant: Represents the ARN of the solution's IAM policy to attach to environment user roles
A_ENVIRONMENT_POLICY_ARN = os.getenv('A_ENVIRONMENT_POLICY_ARN')

# Constant: Represents the account id
A_ACCOUNT_ID = os.getenv('A_ACCOUNT_ID')

# Constant: Represents the arn of the default DataZone permission boundary to restore on environment roles
DEFAULT_DATAZONE_PERMISSION_BOUNDARY_ARN = 'arn:aws:iam::aws:policy/AmazonDataZoneEnvironmentRolePermissionsBoundary'

# Constant: Represents the arn of the AWS managed policy that allows usage of service catalog and will be removed from environment roles
SERVICE_CATALOG_POLICY_ARN = 'arn:aws:iam::aws:policy/AWSServiceCatalogEndUserFullAccess'

iam = boto3.client('iam')

def handler(event, context):
    """ Function handler: Function that will clean environment roles by 1/ Replacing permission boundary with default one assigned by Amazon DataZone,
    2/ Remove managed policy that extended environment role permissions and 3/ Remove additional attached policies that were not assigned originally by Amazon DataZone

    Parameters
    ----------
    event: dict - Input event dict containing:
        EnvironmentDetails: dict - Dict containing environment details including:
            DomainId: str - Id of DataZone domain
            ProjectId: str - Id of DataZone project
            EnvironmentId: str - Id of DataZone environment
            EnvironmentResources: dict - Dict containing environment associated resources

    context: dict - Input context. Not used on function

    Returns
    -------
    response: dict - Dict with response details including:
        environment_role_arn: str - Cleaned environment role arn (str) 
    """
     
    environment_details = event['EnvironmentDetails']
    domain_id = environment_details['DomainId']
    project_id = environment_details['ProjectId']
    environment_id = environment_details['EnvironmentId']
    environment_resources = environment_details['EnvironmentResources']

    environment_role_arn = environment_resources['userRoleArn']
    environment_role_name = environment_role_arn.split('/')[1]
        
    iam.put_role_permissions_boundary(
        RoleName= environment_role_name,
        PermissionsBoundary= DEFAULT_DATAZONE_PERMISSION_BOUNDARY_ARN
    )
        
    try:
        iam.detach_role_policy(
            RoleName= environment_role_name,
            PolicyArn= A_ENVIRONMENT_POLICY_ARN
        )

        iam.detach_role_policy(
            RoleName= environment_role_name,
            PolicyArn= SERVICE_CATALOG_POLICY_ARN
        )
        
    except: pass

    response = {
        'environment_role_arn': environment_role_arn
    }

    return response

