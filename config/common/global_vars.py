from config.governance.g_config import GOVERNANCE_PROPS

"""
GLOBAL_VARIABLES dict will be used to consolidate global variables to be accessed from everywhere from within solution.
This dict is intended to BE LEFT UNMODIFIED. The dict structure includes:
    account: dict - Dict containing global variables for account (with producer / consumer capabilities) related resources, including:
        a_account_numbers: list - List containing ids of all accounts with producer / consumer capabilities
        a_common_glue_role_name: str - Name to be used in all accounts' role for glue resources
        a_common_lambda_role_name: str - Name to be used in all accounts' role for lambda functions
        a_cross_account_assume_role_name: str - Name to be used in all accounts' role that can be assumed by governance account for cross-account access
        a_update_environment_roles_lambda_name: str - Name to be used in all accounts' lambda function that will update new DataZone environment roles on creation
        a_clean_environment_roles_lambda_name: str - Name to be used in all accounts' lambda function that will clean DataZone environment roles on deletion
    producer: dict - Dict containing global variables for account's producer capability related resources, including:
        p_add_lf_tag_environment_dbs_lambda_name: str - Name to be used in all accounts' lambda function that will tag new DataZone environments' databases in glue catalog with LakeFormation solutions tag
        p_manage_subscription_grant_state_machine_name: str - Name to be used in all accounts' state machine that will orchestrate subscription grant tasks on the producer side
        p_manage_subscription_revoke_state_machine_name: str - Name to be used in all accounts' state machine that will orchestrate subscription revoke tasks on the producer side
    consumer: dict - Dict containing global variables for account's consumer capability related resources, including:
        c_manage_subscription_grant_state_machine_name: str - Name to be used in all accounts' state machine that will orchestrate subscription grant tasks on the consumer side
        c_manage_subscription_revoke_state_machine_name: str - Name to be used in all accounts' state machine that will orchestrate subscription revoke tasks on the consumer side
    governance: dict - Dict containing global variables for governance account related resources, including:
        g_account_number: str- Account id of the governance account
        g_common_stepfunctions_role_name: str - Name of the role for state machines (step functions) in governance account
        g_cross_account_assume_role: str - Name of the role in governance account that can be assumed by accounts with producer / consumer capabilities for cross-account access
        g_p_source_subscriptions_table_name: str - Name of the DynamoDB table in governance account that will store metadata for producer source connection subscriptions details
        g_c_asset_subscriptions_table_name: str - Name of the DynamoDB table in governance account that will store metadata for consumer asset subscriptions details
        g_c_secrets_mapping_table_name: str - Name of the DynamoDB table in governance account that will store metadata for consumer secrets mapping details
"""
GLOBAL_VARIABLES = {
    'account': {
        'a_account_numbers': GOVERNANCE_PROPS['a_account_numbers'],
        'a_common_glue_role_name': 'dz_conn_a_common_glue_role',
        'a_common_lambda_role_name': 'dz_conn_a_common_lambda_role',
        'a_cross_account_assume_role_name': 'dz_conn_a_cross_account_assume_role',
        'a_update_environment_roles_lambda_name': 'dz_conn_a_update_environment_roles',
        'a_clean_environment_roles_lambda_name': 'dz_conn_a_clean_environment_roles'
    },
    'producer': {
        'p_add_lf_tag_environment_dbs_lambda_name': 'dz_conn_p_add_lf_tag_environment_dbs',

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
        
        'g_cross_account_assume_role_name': 'dz_conn_g_cross_account_assume_role',
        'g_p_source_subscriptions_table_name': 'dz_conn_g_p_source_subscriptions',
        'g_c_asset_subscriptions_table_name': 'dz_conn_g_c_asset_subscriptions',
        'g_c_secrets_mapping_table_name': 'dz_conn_g_c_secrets_mapping'
    }
}