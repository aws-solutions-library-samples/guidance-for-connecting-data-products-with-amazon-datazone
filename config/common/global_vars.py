from config.governance.g_config import GOVERNANCE_PROPS

"""
GLOBAL_VARIABLES dict will be used to consolidate global variables to be accessed from everywhere from within solution.
This dict is intended to BE LEFT UNMODIFIED. The dict structure includes:
    account: dict - Dict containing global variables for account (with producer / consumer capabilities) related resources, including:
        a_account_numbers: list - List containing ids of all accounts with producer / consumer capabilities
        a_common_kms_key_alias: str - Alias to be used in all accounts' local kms key
        a_common_glue_role_name: str - Name to be used in all accounts' role for glue resources
        a_common_lambda_role_name: str - Name to be used in all accounts' role for lambda functions
        a_common_stepfunctions_role_name: str - Name to be used in all accounts' role for state machines (step functions)
        a_cross_account_assume_role_name: str - Name to be used in all accounts' role that can be assumed by governance account for cross-account access
        a_project_lambda_inline_policy_name: str - Name to be used in all accounts' inline policy to be assigned to new DataZone project roles
        a_update_project_roles_lambda_name: str - Name to be used in all accounts' lambda function that will update new DataZone project roles on creation
        a_clean_project_roles_lambda_name: str - Name to be used in all accounts' lambda function that will clean DataZone project roles on deletion
        a_manage_service_portfolio_project_roles_access_lambda_name: str - Name to be used in all accounts' lambda function that will (dis)associate all DataZone projects to accounts service portfolio on solution deployment / deletion
    producer: dict - Dict containing global variables for account's producer capability related resources, including:
        p_aws_sdk_pandas_account_id: str - Account id hosting AWS SDK for Pandas serverless application. Used as lambda layer when connecting to database sources from producer workflow.
        p_pyodbc_layer_name: str - Name of the lambda layer to be created and used for pyodbc library.
        p_oracledb_layer_name: str - Name of the lambda layer to be created and used for oracledb library.
        p_lakeformation_tag_key: str - Key to be used in all accounts' Lake Formation tag to be used for tagging all DataZone project databases in glue catalog
        p_lakeformation_tag_value: str - Value to be used in all accounts' Lake Formation tag to be used for tagging all DataZone project databases in glue catalog
        p_add_lf_tag_project_dbs_lambda_name: str - Name to be used in all accounts' lambda function that will tag new DataZone projects' databases in glue catalog with LakeFormation solutions tag
        p_manage_subscription_grant_state_machine_name: str - Name to be used in all accounts' state machine that will orchestrate subscription grant tasks on the producer side
        p_manage_subscription_revoke_state_machine_name: str - Name to be used in all accounts' state machine that will orchestrate subscription revoke tasks on the producer side
    consumer: dict - Dict containing global variables for account's consumer capability related resources, including:
        c_manage_subscription_grant_state_machine_name: str - Name to be used in all accounts' state machine that will orchestrate subscription grant tasks on the consumer side
        c_manage_subscription_revoke_state_machine_name: str - Name to be used in all accounts' state machine that will orchestrate subscription revoke tasks on the consumer side
    governance: dict - Dict containing global variables for governance account related resources, including:
        g_account_number: str- Account id of the governance account
        g_common_stepfunctions_role_name: str - Name of the role for state machines (step functions) in governance account
        g_common_eventbridge_role_name: str - Name of the role for EventBridge in governance account
        g_cross_account_assume_role: str - Name of the role in governance account that can be assumed by accounts with producer / consumer capabilities for cross-account access
        g_p_source_subscriptions_table_name: str - Name of the DynamoDB table in governance account that will store metadata for producer source connection subscriptions details
        g_c_asset_subscriptions_table_name: str - Name of the DynamoDB table in governance account that will store metadata for consumer asset subscriptions details
        g_c_secrets_mapping_table_name: str - Name of the DynamoDB table in governance account that will store metadata for consumer secrets mapping details
"""
GLOBAL_VARIABLES = {
    'account': {
        'a_account_numbers': GOVERNANCE_PROPS['a_account_numbers'],
        'a_common_kms_key_alias': 'dz_conn_a_common_key',
        'a_common_glue_role_name': 'dz_conn_a_common_glue_role',
        'a_common_lambda_role_name': 'dz_conn_a_common_lambda_role',
        'a_common_stepfunctions_role_name': 'dz_conn_a_common_stepfunctions_role',
        'a_cross_account_assume_role_name': 'dz_conn_a_cross_account_assume_role',
        'a_project_lambda_inline_policy_name': 'dz_conn_a_project_lambda_inline_policy',
        'a_update_project_roles_lambda_name': 'dz_conn_a_update_project_roles',
        'a_clean_project_roles_lambda_name': 'dz_conn_a_clean_project_roles',
        'a_manage_service_portfolio_project_roles_access_lambda_name': 'dz_conn_a_manage_service_portfolio_project_roles_access'
    },
    'producer': {
        'p_aws_sdk_pandas_account_id': '336392948345',
        'p_pyodbc_layer_name': 'dz_conn_p_pyodbc_layer',
        'p_oracledb_layer_name': 'dz_conn_p_oracledb_layer',
        'p_lakeformation_tag_key': 'dz_conn_p_access',
        'p_lakeformation_tag_value': 'True',
        'p_add_lf_tag_project_dbs_lambda_name': 'dz_conn_p_add_lf_tag_project_dbs',

        'p_manage_subscription_grant_state_machine_name': 'dz_conn_p_manage_subscription_grant',
        'p_manage_subscription_revoke_state_machine_name': 'dz_conn_p_manage_subscription_revoke'
    },
    'consumer': {
        'c_manage_subscription_grant_state_machine_name': 'dz_conn_c_manage_subscription_grant',
        'c_manage_subscription_revoke_state_machine_name': 'dz_conn_c_manage_subscription_revoke'
    },
    'governance': {
        'g_account_number': GOVERNANCE_PROPS['account_id'],
        'g_common_stepfunctions_role_name': 'dz_conn_g_common_stepfunctions_role',
        'g_common_eventbridge_role_name': 'dz_conn_g_common_eventbridge_role',
        
        'g_cross_account_assume_role': 'dz_conn_g_cross_account_assume_role',
        'g_p_source_subscriptions_table_name': 'dz_conn_g_p_source_subscriptions',
        'g_c_asset_subscriptions_table_name': 'dz_conn_g_c_asset_subscriptions',
        'g_c_secrets_mapping_table_name': 'dz_conn_g_c_secrets_mapping'
    }
}