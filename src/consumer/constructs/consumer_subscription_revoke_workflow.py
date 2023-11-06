from config.common.global_vars import GLOBAL_VARIABLES

from aws_cdk import (
    Environment,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_stepfunctions as stepfunctions,
    aws_logs as logs
)

from os import path;

from constructs import Construct

class ConsumerManageSubscriptionRevokeWorkflowConstruct(Construct):
    """ Class to represent the workflow that will execute in the consumer account after a Amazon DataZone subscription is revoked.
    The workflow will delete the local secret if not additional grants are supported by it. Metadata will be updated in dynamodb tables hosted on governance account.
    Actions involving governance account resources will be done via cross-account access.
    """

    def __init__(self, scope: Construct, construct_id: str, account_props: dict, workflow_props: dict, common_constructs: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will create a workflow (state machine and belonging lambda functions) based on properties specified as parameter.
        
        Parameters
        ----------
        account_props : dict
            dict with common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        workflow_props : dict
            dict with required properties for workflow creation.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        common_constructs: dic
            dict with constructs common to the account. Created in and output of account common stack.
        
        env: Environment
            Environment object with region and account details
        """

        super().__init__(scope, construct_id, **kwargs)
        account_id, region = account_props['account_id'], account_props['region']
        
        # ---------------- Lambda ------------------------
        c_delete_subscription_secret_lambda = lambda_.Function(
            scope= self,
            id= 'c_delete_subscription_secret_lambda',
            function_name= 'dz_conn_c_delete_subscription_secret',
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/consumer/code/lambda', "delete_subscription_secret")),
            handler= "delete_subscription_secret.handler",
            role= common_constructs['a_common_lambda_role'],
            environment= {
                'G_ACCOUNT_ID': GLOBAL_VARIABLES['governance']['g_account_number'],
                'G_CROSS_ACCOUNT_ASSUME_ROLE_NAME': GLOBAL_VARIABLES['governance']['g_cross_account_assume_role_name'],
                'G_C_SECRETS_MAPPING_TABLE_NAME': GLOBAL_VARIABLES['governance']['g_c_secrets_mapping_table_name'],
                'RECOVERY_WINDOW_IN_DAYS': workflow_props['secret_recovery_window_in_days']
            }
        )

        c_remove_subscription_records_lambda = lambda_.Function(
            scope= self,
            id= 'c_remove_subscription_records_lambda',
            function_name= 'dz_conn_c_remove_subscription_records',
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/consumer/code/lambda', "remove_subscription_records")),
            handler= "remove_subscription_records.handler",
            role= common_constructs['a_common_lambda_role'],
            environment= {
                'G_ACCOUNT_ID': GLOBAL_VARIABLES['governance']['g_account_number'],
                'G_CROSS_ACCOUNT_ASSUME_ROLE_NAME': GLOBAL_VARIABLES['governance']['g_cross_account_assume_role_name'],
                'G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME': GLOBAL_VARIABLES['governance']['g_c_asset_subscriptions_table_name']
            }
        )
        
        # ---------------- Step Functions ------------------------    
        c_manage_subscription_revoke_state_machine_name = GLOBAL_VARIABLES['consumer']['c_manage_subscription_revoke_state_machine_name']

        c_manage_subscription_revoke_state_machine_logs = logs.LogGroup(
            scope= self,
            id= 'c_manage_subscription_revoke_state_machine_logs',
            log_group_name=f'/aws/step-functions/{c_manage_subscription_revoke_state_machine_name}',
            removal_policy=RemovalPolicy.DESTROY
        )

        c_manage_subscription_revoke_state_machine = stepfunctions.StateMachine(
            scope= self,
            id= 'c_manage_subscription_revoke_state_machine',
            state_machine_name= GLOBAL_VARIABLES['consumer']['c_manage_subscription_revoke_state_machine_name'],
            definition_body=stepfunctions.DefinitionBody.from_file('src/consumer/code/stepfunctions/consumer_manage_subscription_revoke_workflow.asl.json'),
            definition_substitutions= {
                'c_delete_subscription_secret_lambda_arn': c_delete_subscription_secret_lambda.function_arn,
                'c_remove_subscription_records_lambda_arn': c_remove_subscription_records_lambda.function_arn
            },
            role= common_constructs['a_common_sf_role'],
            logs= stepfunctions.LogOptions(
                destination=c_manage_subscription_revoke_state_machine_logs,
                level=stepfunctions.LogLevel.ALL
            ),
            tracing_enabled=True
        )

