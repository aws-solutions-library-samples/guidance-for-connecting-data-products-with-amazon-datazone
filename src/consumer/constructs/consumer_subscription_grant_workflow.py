from config.common.global_vars import GLOBAL_VARIABLES

from aws_cdk import (
    Environment,
    aws_lambda as lambda_,
    aws_stepfunctions as stepfunctions,
)

from os import path;

from constructs import Construct

class ConsumerManageSubscriptionGrantWorkflowConstruct(Construct):
    """ Class to represent the workflow that will execute in the consumer account after a Amazon DataZone subscription is approved.
    The workflow will copy the secret shared by the producer account into a local one with access only for project owning the subscription. Metadata will be updated in dynamodb tables hosted on governance account.
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
        c_copy_subscription_secret_lambda = lambda_.Function(
            scope= self,
            id= 'c_copy_subscription_secret_lambda',
            function_name= 'dz_conn_c_copy_subscription_secret',
            runtime= lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset(path.join('src/consumer/code/lambda', "copy_subscription_secret")),
            handler= "copy_subscription_secret.handler",
            role= common_constructs['a_common_lambda_role'],
            environment= {
                'G_ACCOUNT_ID': GLOBAL_VARIABLES['governance']['g_account_number'],
                'G_CROSS_ACCOUNT_ASSUME_ROLE_NAME': GLOBAL_VARIABLES['governance']['g_cross_account_assume_role'],
                'G_C_SECRETS_MAPPING_TABLE_NAME': GLOBAL_VARIABLES['governance']['g_c_secrets_mapping_table_name'],
                'A_COMMON_KEY_ALIAS': common_constructs['a_common_key_alias'],
                'ACCOUNT_ID': account_id
            }
        )

        c_update_subscription_records_lambda = lambda_.Function(
            scope= self,
            id= 'c_update_subscription_records_lambda',
            function_name= 'dz_conn_c_update_subscription_records',
            runtime= lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset(path.join('src/consumer/code/lambda', "update_subscription_records")),
            handler= "update_subscription_records.handler",
            role= common_constructs['a_common_lambda_role'],
            environment= {
                'G_ACCOUNT_ID': GLOBAL_VARIABLES['governance']['g_account_number'],
                'G_CROSS_ACCOUNT_ASSUME_ROLE_NAME': GLOBAL_VARIABLES['governance']['g_cross_account_assume_role'],
                'G_C_SECRETS_MAPPING_TABLE_NAME': GLOBAL_VARIABLES['governance']['g_c_secrets_mapping_table_name'],
                'G_C_ASSET_SUBSCRIPTIONS_TABLE_NAME': GLOBAL_VARIABLES['governance']['g_c_asset_subscriptions_table_name'],
                'ACCOUNT_ID': account_id
            }
        )
        
        # ---------------- Step Functions ------------------------    
        c_manage_subscription_grant_state_machine = stepfunctions.StateMachine(
            scope= self,
            id= 'c_manage_subscription_grant_state_machine',
            state_machine_name= GLOBAL_VARIABLES['consumer']['c_manage_subscription_grant_state_machine_name'],
            definition_body=stepfunctions.DefinitionBody.from_file('src/consumer/code/stepfunctions/consumer_manage_subscription_grant_workflow.asl.json'),
            definition_substitutions= {
                'c_copy_subscription_secret_lambda_arn': c_copy_subscription_secret_lambda.function_arn,
                'c_update_subscription_records_lambda_arn': c_update_subscription_records_lambda.function_arn
            },
            role= common_constructs['a_common_sf_role'],
        )

