from config.common.global_vars import GLOBAL_VARIABLES

from aws_cdk import (
    Environment,
    Fn,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_stepfunctions as stepfunctions,
    aws_ec2 as ec2,
    aws_logs as logs
)

from os import path;

from constructs import Construct

class ProducerManageSubscriptionGrantWorkflowConstruct(Construct):
    """ Class to represent the workflow that will execute in the producer account after a Amazon DataZone subscription is approved.
    The workflow will grant access to specified dataset in JDBC source to a new/existing user associated to the subscribing project. Then it will create a secret (if non existent) with project user credentials and share it (only with workflow access) to consumer account. 
    Metadata will be updated in dynamodb tables hosted on governance account.
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
        
        # ---------------- VPC ------------------------
        p_lambda_vpc = ec2.Vpc.from_vpc_attributes( 
            scope= self, 
            id= 'p_lambda_vpc',
            vpc_id= workflow_props['vpc_id'],
            availability_zones = Fn.get_azs(),
            private_subnet_ids = workflow_props['vpc_private_subnet_ids']
        )

        p_lambda_security_group_ids = workflow_props['vpc_security_group_ids']
        p_lambda_security_groups = []
        
        for index, p_lambda_security_group_id in enumerate(p_lambda_security_group_ids):
            p_lambda_security_group = ec2.SecurityGroup.from_security_group_id(
                scope= self, 
                id= f'p_lambda_security_group_{(index + 1):02d}',
                security_group_id= p_lambda_security_group_id,
            )
            
            p_lambda_security_groups.append(p_lambda_security_group)
        
        # ---------------- Lambda ------------------------        
        p_get_connection_details_lambda = lambda_.Function(
            scope= self,
            id= 'p_get_connection_details_lambda',
            function_name= 'dz_conn_p_get_connection_details',
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/producer/code/lambda', "get_connection_details")),
            handler= "get_connection_details.handler",
            role= common_constructs['a_common_lambda_role'],
            environment= {
                'ACCOUNT_ID': account_id,
                'REGION': region
            }
        )
        
        p_grant_jdbc_subscription_lambda = lambda_.Function(
            scope= self,
            id= 'p_grant_jdbc_subscription_lambda',
            function_name= 'dz_conn_p_grant_jdbc_subscription',
            runtime= lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset(path.join('src/producer/code/lambda', "grant_jdbc_subscription")),
            handler= "grant_jdbc_subscription.handler",
            layers= [
                common_constructs['p_aws_sdk_pandas_layer'], 
                common_constructs['p_pyodbc_layer'],
                common_constructs['p_oracledb_layer']
            ],
            role= common_constructs['a_common_lambda_role'],
            vpc= p_lambda_vpc,
            security_groups= p_lambda_security_groups,
            environment= {
                'G_ACCOUNT_ID': GLOBAL_VARIABLES['governance']['g_account_number'],
                'G_CROSS_ACCOUNT_ASSUME_ROLE_NAME': GLOBAL_VARIABLES['governance']['g_cross_account_assume_role_name'],
                'G_P_SOURCE_SUBSCRIPTIONS_TABLE_NAME': GLOBAL_VARIABLES['governance']['g_p_source_subscriptions_table_name'],
                'A_COMMON_KEY_ALIAS': common_constructs['a_common_key_alias'],
                'ACCOUNT_ID': account_id,
                'REGION': region
            }
        )

        p_share_subscription_secret_lambda = lambda_.Function(
            scope= self,
            id= 'p_share_subscription_secret_lambda',
            function_name= 'dz_conn_p_share_subscription_secret',
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/producer/code/lambda', "share_subscription_secret")),
            handler= "share_subscription_secret.handler",
            role= common_constructs['a_common_lambda_role'],
            environment= {
                'ACCOUNT_ID': account_id,
                'C_ROLE_NAME': GLOBAL_VARIABLES['account']['a_common_lambda_role_name']
            }
        )
        
        # ---------------- Step Functions ------------------------    
        p_manage_subscription_grant_state_machine_name = GLOBAL_VARIABLES['producer']['p_manage_subscription_grant_state_machine_name']

        p_manage_subscription_grant_state_machine_logs = logs.LogGroup(
            scope= self,
            id= 'p_manage_subscription_grant_state_machine_logs',
            log_group_name=f'/aws/step-functions/{p_manage_subscription_grant_state_machine_name}',
            removal_policy=RemovalPolicy.DESTROY
        )

        p_manage_subscription_grant_state_machine = stepfunctions.StateMachine(
            scope= self,
            id= 'p_manage_subscription_grant_state_machine',
            state_machine_name= p_manage_subscription_grant_state_machine_name,
            definition_body=stepfunctions.DefinitionBody.from_file('src/producer/code/stepfunctions/producer_manage_subscription_grant_workflow.asl.json'),
            definition_substitutions= {
                'p_get_connection_details_lambda_arn': p_get_connection_details_lambda.function_arn,
                'p_grant_jdbc_subscription_lambda_arn': p_grant_jdbc_subscription_lambda.function_arn,
                'p_share_subscription_secret_lambda_arn': p_share_subscription_secret_lambda.function_arn
            },
            role= common_constructs['a_common_sf_role'],
            logs= stepfunctions.LogOptions(
                destination=p_manage_subscription_grant_state_machine_logs,
                level=stepfunctions.LogLevel.ALL
            ),
            tracing_enabled=True
        )

