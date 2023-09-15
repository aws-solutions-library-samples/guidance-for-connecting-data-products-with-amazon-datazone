from config.common.global_vars import GLOBAL_VARIABLES

from aws_cdk import (
    Stack,
    Environment,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_iam as iam
)

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
                name= 'datazone_consumer_project_id',
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
                name= 'datazone_consumer_project_id', 
                type= dynamodb.AttributeType.STRING
            ),
            sort_key= dynamodb.Attribute(
                name= 'datazone_asset_name',
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
                name= 'datazone_producer_shared_secret_arn', 
                type= dynamodb.AttributeType.STRING
            ),
            billing_mode= dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy= RemovalPolicy.DESTROY
        )

        g_dynamodb_tables.append(g_c_secrets_mapping_table)

        # ----------------------- IAM for Account Cross-Account Access ---------------------------
        a_common_lambda_role_name = GLOBAL_VARIABLES['account']['a_common_lambda_role_name']
        a_account_ids = governance_props['a_account_numbers']
        
        g_cross_account_assume_role = iam.Role(
            scope= self,
            id= 'g_cross_account_assume_role',
            role_name= GLOBAL_VARIABLES['governance']['g_cross_account_assume_role'],
            assumed_by= iam.ServicePrincipal('lambda.amazonaws.com')
        )

        if a_account_ids:
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

        g_cross_account_assume_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess'))
        g_cross_account_assume_role.add_managed_policy(g_cross_account_assume_role_policy)

        # ----------------------- IAM for Step Functions ---------------------------
        g_common_sf_role = iam.Role(
            scope= self,
            id= 'g_common_sf_role',
            role_name= GLOBAL_VARIABLES['governance']['g_common_stepfunctions_role_name'],
            assumed_by= iam.ServicePrincipal('states.amazonaws.com')
        )
        
        g_common_sf_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess'))

        g_common_sf_policy = iam.ManagedPolicy(
            scope= self,
            id= 'g_common_sf_policy',
            managed_policy_name= 'g_common_sf_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['lambda:InvokeFunction'],
                    resources=[f'arn:aws:lambda:{region}:{account_id}:function:*']
                ),
                iam.PolicyStatement(
                    actions=['sts:AssumeRole'],
                    resources=['*']
                )
            ]
        )

        g_common_sf_role.add_managed_policy(g_common_sf_policy)

        # ----------------------- IAM for EventBridge ---------------------------
        g_common_eventbridge_role = iam.Role(
            scope= self,
            id= 'g_common_eventbridge_role',
            role_name= GLOBAL_VARIABLES['governance']['g_common_eventbridge_role_name'],
            assumed_by= iam.ServicePrincipal('events.amazonaws.com')
        )

        g_common_eventbridge_policy = iam.ManagedPolicy(
            scope= self,
            id= 'g_common_eventbridge_policy',
            managed_policy_name= 'g_common_eventbridge_policy',
            statements= [
                iam.PolicyStatement(
                    actions=['states:StartExecution'],
                    resources=[f'arn:aws:states:{region}:{account_id}:stateMachine:*']
                )
            ]
        )

        g_common_eventbridge_role.add_managed_policy(g_common_eventbridge_policy)

        # -------------- Outputs --------------------
        self.outputs = {
            'g_p_source_subscriptions_table': g_p_source_subscriptions_table,
            'g_c_asset_subscriptions_table': g_c_asset_subscriptions_table,
            'g_c_secrets_mapping_table': g_c_secrets_mapping_table,
            'g_common_sf_role': g_common_sf_role,
            'g_common_eventbridge_role_name': g_common_eventbridge_role.role_name,
        }
