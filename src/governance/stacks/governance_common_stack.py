from config.common.global_vars import GLOBAL_VARIABLES

from aws_cdk import (
    Stack,
    Environment,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_
)

from os import path

from constructs import Construct

class DataZoneConnectorsGovernanceCommonStack(Stack):
    """ Class to represents the stack containing all common resources in governance account."""

    def __init__(self, scope: Construct, construct_id: str, governance_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will deploy common resources in governance account based on properties specified as parameter.
        
        Parameters
        ----------
        governance_props : dict
            dict with common properties for governance account.
            For more details check config/governance/g_config.py documentation and examples.

        common_constructs: dic
            dict with constructs common to the governance account. Created in and output of governance common stack.
        
        env: Environment
            Environment object with region and account details
        """
        
        super().__init__(scope, construct_id, **kwargs)
        account_id, region = governance_props['account_id'], governance_props['region']

        # ----------------------- DynamoDB ---------------------------
        g_dynamodb_tables = []
        
        g_p_source_subscriptions_table = dynamodb.Table(
            scope= self, 
            id= 'g_p_source_subscriptions_table',
            table_name= GLOBAL_VARIABLES['governance']['g_p_source_subscriptions_table_name'],
            partition_key= dynamodb.Attribute(
                name= 'glue_connection_arn', 
                type= dynamodb.AttributeType.STRING
            ),
            sort_key= dynamodb.Attribute(
                name= 'datazone_consumer_environment_id',
                type= dynamodb.AttributeType.STRING
            ),
            billing_mode= dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy= RemovalPolicy.DESTROY
        )

        g_dynamodb_tables.append(g_p_source_subscriptions_table)
        
        g_c_asset_subscriptions_table = dynamodb.Table(
            scope= self, 
            id= 'g_c_asset_subscriptions_table',
            table_name= GLOBAL_VARIABLES['governance']['g_c_asset_subscriptions_table_name'],
            partition_key= dynamodb.Attribute(
                name= 'datazone_consumer_environment_id', 
                type= dynamodb.AttributeType.STRING
            ),
            sort_key= dynamodb.Attribute(
                name= 'datazone_asset_id',
                type= dynamodb.AttributeType.STRING
            ),
            billing_mode= dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy= RemovalPolicy.DESTROY
        )

        g_dynamodb_tables.append(g_c_asset_subscriptions_table)

        g_c_secrets_mapping_table = dynamodb.Table(
            scope= self, 
            id= 'g_c_secrets_mapping_table',
            table_name= GLOBAL_VARIABLES['governance']['g_c_secrets_mapping_table_name'],
            partition_key= dynamodb.Attribute(
                name= 'shared_secret_arn', 
                type= dynamodb.AttributeType.STRING
            ),
            billing_mode= dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy= RemovalPolicy.DESTROY
        )

        g_dynamodb_tables.append(g_c_secrets_mapping_table)

        # ----------------------- IAM for Account Cross-Account Access ---------------------------
        a_account_ids = governance_props['a_account_numbers']
        
        g_cross_account_assume_role = iam.Role(
            scope= self,
            id= 'g_cross_account_assume_role',
            role_name= GLOBAL_VARIABLES['governance']['g_cross_account_assume_role_name'],
            assumed_by= iam.ServicePrincipal('lambda.amazonaws.com')
        )

        if a_account_ids:
            a_common_lambda_role_name = GLOBAL_VARIABLES['account']['a_common_lambda_role_name']
            g_cross_account_assume_trust_policy = iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                principals=[iam.AnyPrincipal()],
                conditions={
                    "StringEquals": {
                        "aws:PrincipalAccount": a_account_ids,
                    },
                    "ArnLike": {
                        "aws:PrincipalArn": f"arn:aws:iam::*:role/{a_common_lambda_role_name}"
                    }
                }
            )

            g_cross_account_assume_role.assume_role_policy.add_statements(g_cross_account_assume_trust_policy)

        g_cross_account_assume_role_policy = iam.ManagedPolicy(
            scope= self,
            id= 'g_cross_account_assume_role_policy',
            managed_policy_name= 'g_cross_account_assume_role_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['dynamodb:Query', 'dynamodb:GetItem', 'dynamodb:putItem', 'dynamodb:UpdateItem', 'dynamodb:BatchWriteItem', 'dynamodb:DeleteItem'],
                    resources=[dynamodb_table.table_arn for dynamodb_table in g_dynamodb_tables]
                )
            ]
        )

        g_cross_account_assume_role.add_managed_policy(g_cross_account_assume_role_policy)

        # ----------------------- IAM for Lambda & Step Functions ---------------------------
        g_common_lambda_role = iam.Role(
            scope= self,
            id= 'g_common_lambda_role',
            role_name= 'dz_conn_g_common_lambda_role',
            assumed_by= iam.ServicePrincipal('lambda.amazonaws.com')
        )

        g_common_lambda_policy = iam.ManagedPolicy(
            scope= self,
            id= 'g_common_lambda_policy',
            managed_policy_name= 'g_common_lambda_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['datazone:GetEnvironment', 'datazone:GetEnvironmentBlueprint', 'datazone:GetListing', 'datazone:GetProject', 'datazone:GetEnvironment', 'datazone:GetEnvironmentProfile', 'datazone:ListEnvironments'],
                    resources=[f'arn:aws:datazone:{region}:{account_id}:domain/*']
                ),
                iam.PolicyStatement(
                    actions=['states:StartExecution'],
                    resources=[f'arn:aws:states:{region}:{account_id}:stateMachine:dz_conn_g_*']
                ),
                iam.PolicyStatement(
                    actions=['logs:CreateLogGroup'],
                    resources=[f'arn:aws:logs:{region}:{account_id}:*']
                ),
                iam.PolicyStatement(
                    actions=['logs:CreateLogStream', 'logs:PutLogEvents'],
                    resources=[f'arn:aws:logs:{region}:{account_id}:log-group:/aws/lambda/dz_conn_g_*']
                )
            ]
        )

        g_common_lambda_role.add_managed_policy(g_common_lambda_policy)
        
        g_common_sf_role = iam.Role(
            scope= self,
            id= 'g_common_sf_role',
            role_name= GLOBAL_VARIABLES['governance']['g_common_stepfunctions_role_name'],
            assumed_by= iam.ServicePrincipal('states.amazonaws.com')
        )

        g_common_sf_policy = iam.ManagedPolicy(
            scope= self,
            id= 'g_common_sf_policy',
            managed_policy_name= 'g_common_sf_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['lambda:InvokeFunction'],
                    resources=[f'arn:aws:lambda:{region}:{account_id}:function:dz_conn_g_*']
                ),
                iam.PolicyStatement(
                    actions=['logs:CreateLogGroup', 'logs:DescribeLogGroups'],
                    resources=[f'arn:aws:logs:{region}:{account_id}:*']
                ),
                iam.PolicyStatement(
                    actions=['logs:CreateLogDelivery', 'logs:CreateLogStream', 'logs:GetLogDelivery', 'logs:UpdateLogDelivery', 'logs:ListLogDeliveries', 'logs:DeleteLogDelivery', 'logs:PutLogEvents', 'logs:PutResourcePolicy', 'logs:DescribeResourcePolicies'],
                    resources=[f'arn:aws:logs:{region}:{account_id}:log-group:/aws/step-functions/dz_conn_g_*']
                ),
                iam.PolicyStatement(
                    actions=['xray:PutTraceSegments', 'xray:PutTelemetryRecords', 'xray:GetSamplingRules', 'xray:GetSamplingTargets'],
                    resources=[f'arn:aws:xray:{region}:{account_id}:*']
                )
            ]
        )

        if a_account_ids:
            a_cross_account_assume_role_name = GLOBAL_VARIABLES['account']['a_cross_account_assume_role_name']
            g_common_sf_assume_role_policy_statement = iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                resources=[f'arn:aws:iam::{a_account_id}:role/{a_cross_account_assume_role_name}' for a_account_id in a_account_ids],
            )

            g_common_sf_policy.add_statements(g_common_sf_assume_role_policy_statement)

        g_common_sf_role.add_managed_policy(g_common_sf_policy)

        # ----------------------- IAM for EventBridge ---------------------------
        g_common_eventbridge_role = iam.Role(
            scope= self,
            id= 'g_common_eventbridge_role',
            role_name= 'dz_conn_g_common_eventbridge_role',
            assumed_by= iam.ServicePrincipal('events.amazonaws.com')
        )

        g_common_eventbridge_policy = iam.ManagedPolicy(
            scope= self,
            id= 'g_common_eventbridge_policy',
            managed_policy_name= 'g_common_eventbridge_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['states:StartExecution'],
                    resources=[f'arn:aws:states:{region}:{account_id}:stateMachine:dz_conn_g_*']
                ),
                iam.PolicyStatement(
                    actions=['lambda:InvokeFunction'],
                    resources=[f'arn:aws:lambda:{region}:{account_id}:function:dz_conn_g_*']
                )
            ]
        )

        g_common_eventbridge_role.add_managed_policy(g_common_eventbridge_policy)

        # ---------------- Lambda Layer ------------------------
        g_boto3_layer = lambda_.LayerVersion(
            scope=self, 
            id='g_boto3_layer',
            layer_version_name='dz_conn_g_boto3_layer',
            code=lambda_.AssetCode('libs/python311/boto3-layer.zip'),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11]
        )

        # ---------------- Lambda ------------------------        
        g_get_environment_details_lambda = lambda_.Function(
            scope= self,
            id= 'g_get_environment_details_lambda',
            function_name= 'dz_conn_g_get_environment_details',
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/governance/code/lambda', "get_environment_details")),
            handler= "get_environment_details.handler",
            layers= [
                g_boto3_layer
            ],
            role= g_common_lambda_role
        )

        g_get_subscription_details_lambda = lambda_.Function(
            scope= self,
            id= 'g_get_subscription_details_lambda',
            function_name= 'dz_conn_g_get_subscription_details',
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/governance/code/lambda', "get_subscription_details")),
            handler= "get_subscription_details.handler",
            layers= [
                g_boto3_layer
            ],
            role= g_common_lambda_role
        )

        g_manage_subscription_grant_state_machine_name = GLOBAL_VARIABLES['governance']['g_manage_subscription_grant_state_machine_name']
        g_manage_subscription_revoke_state_machine_name = GLOBAL_VARIABLES['governance']['g_manage_subscription_revoke_state_machine_name']
        
        g_start_subscription_workflow_lambda = lambda_.Function(
            scope= self,
            id= 'g_start_subscription_workflow_lambda',
            function_name= 'dz_conn_g_start_subscription_workflow',
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/governance/code/lambda', "start_subscription_workflow")),
            handler= "start_subscription_workflow.handler",
            layers= [
                g_boto3_layer
            ],
            role= g_common_lambda_role,
            environment= {
                'G_SUBSCRIPTION_GRANT_WORKFLOW_ARN': f'arn:aws:states:{region}:{account_id}:stateMachine:{g_manage_subscription_grant_state_machine_name}',
                'G_SUBSCRIPTION_REVOKE_WORKFLOW_ARN': f'arn:aws:states:{region}:{account_id}:stateMachine:{g_manage_subscription_revoke_state_machine_name}'
            }
        )

        # -------------- Outputs --------------------
        self.outputs = {
            'g_p_source_subscriptions_table': g_p_source_subscriptions_table,
            'g_c_asset_subscriptions_table': g_c_asset_subscriptions_table,
            'g_c_secrets_mapping_table': g_c_secrets_mapping_table,
            'g_common_lambda_role': g_common_lambda_role,
            'g_common_sf_role': g_common_sf_role,
            'g_common_eventbridge_role_name': g_common_eventbridge_role.role_name,
            'g_get_environment_details_lambda': g_get_environment_details_lambda,
            'g_get_subscription_details_lambda': g_get_subscription_details_lambda,
            'g_start_subscription_workflow_lambda': g_start_subscription_workflow_lambda
        }
