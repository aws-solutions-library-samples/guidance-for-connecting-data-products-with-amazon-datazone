from config.common.global_vars import GLOBAL_VARIABLES

import json
from os import path;

from aws_cdk import (
    Environment,
    Stack,
    Duration,
    CustomResource,
    custom_resources,
    RemovalPolicy,
    aws_kms as kms,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_servicecatalog as servicecatalog,
    aws_s3 as s3
)

from constructs import Construct

class DataZoneConnectorsAccountCommonStack(Stack):
    """ Class to represents the stack containing all common resources in account."""

    def __init__(self, scope: Construct, construct_id: str, account_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will deploy producer-specific common resources in account based on properties specified as parameter.
        
        Parameters
        ----------
        account_props : dict
            dict with common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.
        
        env: Environment
            Environment object with region and account details
        """
        
        super().__init__(scope, construct_id, **kwargs)
        account_id, region = account_props['account_id'], account_props['region']

        # ------------------ S3 ------------------------------
        a_bucket= s3.Bucket(
            scope= self,
            id= 'a_bucket',
            bucket_name= account_props['s3']['bucket_name'],
            encryption= s3.BucketEncryption.S3_MANAGED,
            enforce_ssl= True,
            auto_delete_objects= True,
            removal_policy= RemovalPolicy.DESTROY
        )

        # ----------------------- KMS ---------------------------     
        a_common_key_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["kms:*"],
                    principals=[iam.AnyPrincipal()],
                    resources=["*"],
                    conditions={
                        "StringEquals": {
                            "kms:CallerAccount": env.account,
                        }
                    }
                ),
                iam.PolicyStatement(
                    actions=["kms:Decrypt", "kms:DescribeKey"],
                    principals=[iam.AnyPrincipal()],
                    resources=["*"],
                    conditions={
                        "StringEquals": {
                            "kms:ViaService": f"secretsmanager.{env.region}.amazonaws.com",
                            "kms:CallerAccount": GLOBAL_VARIABLES['account']['a_account_numbers'],
                        }
                    }
                )
            ]
        )

        a_common_key = kms.Key(
            scope= self,
            id= "a_common_key",
            enable_key_rotation= True,
            pending_window= Duration.days(10),
            policy=a_common_key_policy
        )

        a_common_key_alias_name = 'dz_conn_a_common_key'
        a_common_key.add_alias(f"alias/{a_common_key_alias_name}")
        
        # ----------------------- IAM for DataZone Environments --------------------------- 
        a_environment_permission_boundary_policy_file = open('src/account/code/iam/datazone_custom_environment_permission_boundary.json')
        a_environment_permission_boundary_policy_json = json.load(a_environment_permission_boundary_policy_file)
        a_environment_permission_boundary_policy = iam.ManagedPolicy(
            scope= self,
            id= 'a_environment_permission_boundary_policy',
            managed_policy_name= 'dz_conn_a_environment_permission_boundary_policy',
            document= iam.PolicyDocument.from_json(a_environment_permission_boundary_policy_json)
        )

        a_environment_policy = iam.ManagedPolicy(
            scope= self,
            id= 'a_environment_policy',
            managed_policy_name= 'dz_conn_a_environment_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['s3:Get*', 's3:List*', 's3:Describe*'],
                    resources=[a_bucket.bucket_arn, f'{a_bucket.bucket_arn}/*']
                ),
                iam.PolicyStatement(
                    actions=['lambda:InvokeFunction', 'glue:StartCrawler', 'glue:StopCrawler', 'secretsmanager:GetSecretValue', 'secretsmanager:DescribeSecret'],
                    resources=[
                        f'arn:aws:lambda:{region}:{account_id}:function:*',
                        f'arn:aws:glue:{region}:{account_id}:crawler/*',
                        f'arn:aws:secretsmanager:{region}:{account_id}:secret:*'
                    ],
                    conditions={
                        'StringEquals': {
                            'aws:ResourceTag/AmazonDataZoneEnvironment': '${aws:PrincipalTag/AmazonDataZoneEnvironment}'
                        }
                    }
                ),
                iam.PolicyStatement(
                    actions=['glue:GetCrawler', 'glue:GetCrawlers', 'glue:ListCrawlers', 'glue:BatchGetCrawlers', 'glue:ListCrawls',  'glue:GetConnection', 'glue:GetConnections', 'glue:TestConnection'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['secretsmanager:ListSecrets'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['iam:PassRole'],
                    resources=['arn:aws:iam::*:role/*'],
                    conditions={
                        'StringEquals': {
                            'iam:PassedToService': 'glue.amazonaws.com'
                        }
                    }
                )
            ]
        )

        # ----------------------- IAM for Glue ---------------------------        
        a_common_glue_role = iam.Role(
            scope= self,
            id= 'a_common_glue_role',
            role_name= GLOBAL_VARIABLES['account']['a_common_glue_role_name'],
            assumed_by= iam.ServicePrincipal('glue.amazonaws.com')
        )

        a_common_glue_policy = iam.ManagedPolicy(
            scope= self,
            id= 'p_common_glue_policy',
            managed_policy_name= 'p_common_glue_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['ec2:DescribeVpcs', 'ec2:DescribeNetworkInterfaces', 'ec2:DescribeInternetGateways', 'ec2:DescribeAvailabilityZones', 'ec2:DescribeSubnets', 'ec2:DescribeSecurityGroups'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['secretsmanager:GetSecretValue'],
                    resources=[f'arn:aws:secretsmanager:{region}:{account_id}:secret:*']
                ),
                iam.PolicyStatement(
                    actions=['kms:Decrypt', 'kms:DescribeKey'],
                    resources=[f'arn:aws:kms:{region}:{account_id}:key/*', f'arn:aws:kms:{region}:{account_id}:alias/*']
                ),
                iam.PolicyStatement(
                    actions=['lakeformation:GetDataAccess'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['glue:GetDatabase', 'glue:GetDatabases', 'glue:*Table'],
                    resources=[f'arn:aws:glue:{region}:{account_id}:database/*', f'arn:aws:glue:{region}:{account_id}:table/*']
                )
            ]
        )
        
        a_common_glue_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSGlueServiceRole'))
        a_common_glue_role.add_managed_policy(a_common_glue_policy)

        # ----------------------- IAM for Lambda & Step Functions ---------------------------
        g_account_number = GLOBAL_VARIABLES['governance']["g_account_number"]
        g_cross_account_assume_role_name =  GLOBAL_VARIABLES['governance']["g_cross_account_assume_role_name"]
        
        a_common_lambda_role = iam.Role(
            scope= self,
            id= 'a_common_lambda_role',
            role_name= GLOBAL_VARIABLES['account']['a_common_lambda_role_name'],
            assumed_by= iam.ServicePrincipal('lambda.amazonaws.com')
        )

        a_common_lambda_policy = iam.ManagedPolicy(
            scope= self,
            id= 'a_common_lambda_policy',
            managed_policy_name= 'a_common_lambda_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['iam:PutRolePermissionsBoundary', 'iam:AttachRolePolicy', 'iam:DetachRolePolicy'],
                    resources=[f'arn:aws:iam::{account_id}:role/datazone_usr_*']
                ),
                iam.PolicyStatement(
                    actions=['lakeformation:GetLFTag', 'lakeformation:ListLFTags', 'lakeformation:AddLFTagsToResource', 'lakeformation:RemoveLFTagsFromResource'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['glue:GetDatabase*', 'glue:GetTable*', 'glue:GetConnection*', 'glue:GetCrawler*'],
                    resources=[f'arn:aws:glue:{region}:{account_id}:*']
                ),
                iam.PolicyStatement(
                    actions=['ec2:ModifyNetworkInterfaceAttribute', 'ec2:CreateNetworkInterface', 'ec2:DeleteNetworkInterface'],
                    resources=[f'arn:aws:ec2:{region}:{account_id}:*']
                ),
                iam.PolicyStatement(
                    actions=['ec2:DescribeVpcs', 'ec2:DescribeNetworkInterfaces', 'ec2:DescribeInternetGateways', 'ec2:DescribeAvailabilityZones', 'ec2:DescribeSubnets', 'ec2:DescribeSecurityGroups'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['secretsmanager:GetSecretValue', 'secretsmanager:CreateSecret', 'secretsmanager:DescribeSecret', 'secretsmanager:DeleteSecret', 'secretsmanager:ListSecrets', 'secretsmanager:UpdateSecret', 'secretsmanager:GetResourcePolicy', 'secretsmanager:PutResourcePolicy', "secretsmanager:TagResource"],
                    resources=[f'arn:aws:secretsmanager:{region}:{account_id}:secret:dz-conn-*']
                ),
                iam.PolicyStatement(
                    actions=['secretsmanager:GetSecretValue', 'secretsmanager:DescribeSecret', 'secretsmanager:ListSecrets', 'kms:Decrypt', 'kms:DescribeKey'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['kms:Decrypt', 'kms:DescribeKey', 'kms:Encrypt', 'kms:GenerateDataKey*', 'kms:ReEncrypt*'],
                    resources=[f'arn:aws:kms:{region}:{account_id}:alias/{a_common_key_alias_name}']
                ),
                iam.PolicyStatement(
                    actions=['sts:AssumeRole'],
                    resources=[f'arn:aws:iam::{g_account_number}:role/{g_cross_account_assume_role_name}']
                ),
                iam.PolicyStatement(
                    actions=['servicecatalog:AssociatePrincipalWithPortfolio', 'servicecatalog:DisassociatePrincipalFromPortfolio'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['logs:CreateLogGroup'],
                    resources=[f'arn:aws:logs:{region}:{account_id}:*']
                ),
                iam.PolicyStatement(
                    actions=['logs:CreateLogStream', 'logs:PutLogEvents'],
                    resources=[f'arn:aws:logs:{region}:{account_id}:log-group:/aws/lambda/dz_conn_*']
                )
            ]
        )

        a_common_lambda_role.add_managed_policy(a_common_lambda_policy)

        a_common_sf_role = iam.Role(
            scope= self,
            id= 'a_common_sf_role',
            role_name= 'dz_conn_a_common_stepfunctions_role',
            assumed_by= iam.ServicePrincipal('states.amazonaws.com')
        )

        a_common_sf_policy = iam.ManagedPolicy(
            scope= self,
            id= 'a_common_sf_policy',
            managed_policy_name= 'a_common_sf_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['lambda:InvokeFunction'],
                    resources=[f'arn:aws:lambda:{region}:{account_id}:function:dz_conn_*']
                ),
                iam.PolicyStatement(
                    actions=['logs:CreateLogGroup', 'logs:DescribeLogGroups'],
                    resources=[f'arn:aws:logs:{region}:{account_id}:*']
                ),
                iam.PolicyStatement(
                    actions=['logs:CreateLogDelivery', 'logs:CreateLogStream', 'logs:GetLogDelivery', 'logs:UpdateLogDelivery', 'logs:ListLogDeliveries', 'logs:DeleteLogDelivery', 'logs:PutLogEvents', 'logs:PutResourcePolicy', 'logs:DescribeResourcePolicies'],
                    resources=[f'arn:aws:logs:{region}:{account_id}:log-group:/aws/step-functions/dz_conn_*']
                ),
                iam.PolicyStatement(
                    actions=['xray:PutTraceSegments', 'xray:PutTelemetryRecords', 'xray:GetSamplingRules', 'xray:GetSamplingTargets'],
                    resources=[f'arn:aws:xray:{region}:{account_id}:*']
                )
            ]
        )

        a_common_sf_role.add_managed_policy(a_common_sf_policy)

        # ---------------- Lambda ------------------------
        a_update_environment_roles_lambda = lambda_.Function(
            scope= self,
            id= 'a_update_environment_roles_lambda',
            function_name= GLOBAL_VARIABLES["account"]["a_update_environment_roles_lambda_name"],
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/account/code/lambda', "update_environment_roles")),
            handler= "update_environment_roles.handler",
            role= a_common_lambda_role,
            environment= {
                'A_ENVIRONMENT_POLICY_ARN': a_environment_policy.managed_policy_arn,
                'A_PERMISSION_BOUNDARY_POLICY_ARN': a_environment_permission_boundary_policy.managed_policy_arn,
                'A_REGION': region,
                'A_ACCOUNT_ID':account_id
            }
        )

        a_clean_environment_roles_lambda = lambda_.Function(
            scope= self,
            id= 'a_clean_environment_roles_lambda',
            function_name= GLOBAL_VARIABLES["account"]["a_clean_environment_roles_lambda_name"],
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/account/code/lambda', "clean_environment_roles")),
            handler= "clean_environment_roles.handler",
            role= a_common_lambda_role,
            environment= {
                'A_ENVIRONMENT_POLICY_ARN': a_environment_policy.managed_policy_arn,
                'A_ACCOUNT_ID':account_id
            }
        )

        # ----------------------- IAM for Governance Cross-Account Access --------------------------- 
        g_common_stepfunctions_role_name = GLOBAL_VARIABLES['governance']["g_common_stepfunctions_role_name"]
        g_common_stepfunctions_role_arn = f'arn:aws:iam::{g_account_number}:role/{g_common_stepfunctions_role_name}'
        
        a_cross_account_assume_role = iam.Role(
            scope= self,
            id= 'a_cross_account_assume_role',
            role_name= GLOBAL_VARIABLES['account']['a_cross_account_assume_role_name'],
            assumed_by= iam.ServicePrincipal('states.amazonaws.com')
        )

        a_cross_account_assume_trust_policy = iam.PolicyStatement(
            actions=["sts:AssumeRole"],
            principals=[
                iam.ArnPrincipal(g_common_stepfunctions_role_arn)
            ]
        )

        a_cross_account_assume_role.assume_role_policy.add_statements(a_cross_account_assume_trust_policy)

        a_cross_account_assume_policy = iam.ManagedPolicy(
            scope= self,
            id= 'a_cross_account_assume_policy',
            managed_policy_name= 'dz_conn_a_cross_account_assume_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['states:DescribeStateMachine', 'states:StartExecution', 'states:StartSyncExecution', 'states:ListExecutions', 'states:DescribeExecution', 'states:StopExecution'],
                    resources=[f'arn:aws:states:{region}:{account_id}:stateMachine:dz_conn_*', f'arn:aws:states:{region}:{account_id}:execution:dz_conn_*']
                ),
                iam.PolicyStatement(
                    actions=['lambda:InvokeFunction'],
                    resources=[f'arn:aws:lambda:{region}:{account_id}:function:dz_conn_*']
                )
            ]
        )

        a_cross_account_assume_role.add_managed_policy(a_cross_account_assume_policy)

        # ------------------ Service Catalog Portfolio ------------------------------
        a_service_portfolio = servicecatalog.Portfolio(
            scope= self, 
            id= 'a_service_portfolio',
            display_name='DataZone Connectors Toolkit - Service Portfolio',
            description='Portfolio for DataZone Connectors toolkit',
            provider_name='Data Governance Team'
        )

        a_service_portfolio.node.add_dependency(a_common_lambda_role)

        a_portfolio_access_role_names = set(account_props['service_portfolio']['access_role_names'])
        a_portfolio_access_role_names.add(GLOBAL_VARIABLES['account']['a_common_lambda_role_name'])
        
        for a_access_role_name in a_portfolio_access_role_names:
            
            a_access_role_id = a_access_role_name.lower().replace('-', '_')
            a_access_role = iam.Role.from_role_name(
                scope= self,
                id= f'a_access_role_{a_access_role_id}',
                role_name= a_access_role_name
            )

            a_service_portfolio.give_access_to_role(a_access_role)

        a_manage_service_portfolio_environment_roles_access_lambda = lambda_.Function(
            scope= self,
            id= 'a_manage_service_portfolio_environment_roles_access_lambda',
            function_name= 'dz_conn_a_manage_service_portfolio_environment_roles_access',
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/account/code/lambda', "manage_service_portfolio_environment_roles_access")),
            handler= "manage_service_portfolio_environment_roles_access.handler",
            role= a_common_lambda_role,
            environment= {
                'A_SERVICE_PORTFOLIO_ID': a_service_portfolio.portfolio_id
            }
        )

        a_manage_service_portfolio_environment_roles_access_provider = custom_resources.Provider(
            scope= self,
            id= 'a_manage_service_portfolio_environment_roles_access_provider',
            on_event_handler= a_manage_service_portfolio_environment_roles_access_lambda
        )

        a_manage_service_portfolio_environment_roles_access_custom_resource = CustomResource(
            scope= self,
            id= 'a_manage_service_portfolio_environment_roles_access_custom_resource',
            resource_type='Custom::LambdaCustomResource',
            service_token= a_manage_service_portfolio_environment_roles_access_provider.service_token
        )
        
        # -------------- Outputs --------------------
        self.outputs = {
            'a_bucket': a_bucket,
            'a_common_key': a_common_key,
            'a_common_key_alias': a_common_key_alias_name,
            'a_environment_permission_boundary_policy': a_environment_permission_boundary_policy,
            'a_environment_policy': a_environment_policy,
            'a_common_glue_role': a_common_glue_role,
            'a_common_lambda_role': a_common_lambda_role,
            'a_common_sf_role': a_common_sf_role,
            'a_update_environment_roles_lambda': a_update_environment_roles_lambda,
            'a_clean_environment_roles_lambda': a_clean_environment_roles_lambda,
            'a_cross_account_assume_role': a_cross_account_assume_role,
            'a_service_portfolio_arn': a_service_portfolio.portfolio_arn
        }
