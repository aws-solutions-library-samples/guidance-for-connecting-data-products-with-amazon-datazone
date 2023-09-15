import os
import json

import boto3

# Constant: Represents the name of the inline policy to be added to project roles
A_PROJECT_LAMBDA_INLINE_POLICY_NAME = os.getenv('A_PROJECT_LAMBDA_INLINE_POLICY_NAME')

# Constant: Represents the arn of the custom permission boundary that will be assigned to project roles
A_PERMISSION_BOUNDARY_POLICY_ARN = os.getenv('A_PERMISSION_BOUNDARY_POLICY_ARN')

# Constant: Represents the region
A_REGION = os.getenv('A_REGION')

# Constant: Represents the account id
A_ACCOUNT_ID = os.getenv('A_ACCOUNT_ID')

# Constant: Represents the arn of the AWS managed policy that allows usage of service catalog and will be added to project roles
SERVICE_CATALOG_POLICY_ARN = 'arn:aws:iam::aws:policy/AWSServiceCatalogEndUserFullAccess'

# Constant: Represents a list of prefixes used by DataZone when creating project roles.
PROJECT_ROLE_PREFIXES = ['datazone-usr-c', 'datazone-usr-o', 'datazone-usr-v']

iam = boto3.client('iam')

def handler(event, context):
    """ Function handler: Function that will update project roles by 1/ Replacing default permission boundary with a custom more permissive one,
    2/ Add an inline policy that extends project role permissions and 3/ Attach additional policies that were not assigned originally by Amazon DataZone

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
            PermissionsBoundary= A_PERMISSION_BOUNDARY_POLICY_ARN
        )

        iam.attach_role_policy(
            RoleName= project_role_name,
            PolicyArn= SERVICE_CATALOG_POLICY_ARN
        )

        add_project_role_inline_policy(project_role_name, project_id)
        project_role_arn = f'arn:aws:iam::{A_ACCOUNT_ID}:role/{project_role_name}'
        project_role_arns.append(project_role_arn)

    response = {
        'project_role_arns': project_role_arns
    }

    return response


def add_project_role_inline_policy(project_role_name, project_id):
    """ Complementary function to add a custom inline policy to a specific project role"""

    project_lambda_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction",
                    "glue:StartCrawler",
                    "glue:StopCrawler",
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret"
                ],
                "Resource": [
                    f"arn:aws:lambda:{A_REGION}:{A_ACCOUNT_ID}:function:*",
                    f"arn:aws:glue:{A_REGION}:{A_ACCOUNT_ID}:crawler/*",
                    f"arn:aws:secretsmanager:{A_REGION}:{A_ACCOUNT_ID}:secret:*",
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceTag/datazone:projectId": project_id
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "glue:GetCrawler",
                    "glue:GetCrawlers",
                    "glue:ListCrawlers",
                    "glue:ListCrawls",
                    "glue:GetConnection",
                    "glue:GetConnections",
                    "glue:TestConnection",
                    "glue:BatchGetCrawlers",
                    "secretsmanager:ListSecrets"
                ],
                "Resource": [
                    "*"
                ]
            }
        ]
    }

    iam.put_role_policy(
        RoleName= project_role_name,
        PolicyName= A_PROJECT_LAMBDA_INLINE_POLICY_NAME,
        PolicyDocument= json.dumps(project_lambda_policy)
    )
