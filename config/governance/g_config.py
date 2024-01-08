# ------------------ Governance ------------------------

"""
GOVERNANCE_PROPS dict will be used to consolidate common properties for governance account.
The dict structures includes:
    account_id: str - Account id
    region: str - Region
    a_account_numbers: list - List containing ids of all accounts with producer / consumer capabilities (governed)
"""
GOVERNANCE_PROPS = {
    'account_id': '',
    'region': '',
    'a_account_numbers': [],
}

"""
GOVERNANCE_WORKFLOW_PROPS dict will be used to consolidate governance workflow properties for governance account.
The dict structures includes a key (not to be modified) per workflow:
    g_manage_environment_active: dict - Dict containing properties for managing when a new environment is active including:
        g_eventbridge_rule_enabled: bool - If workflow is enabled or not, meaning will execute on event or not.
    g_manage_environment_delete: dict - Dict containing properties for managing when a environment is going to be deleted including:
        g_eventbridge_rule_enabled: bool - If workflow is enabled or not, meaning will execute on event or not.
    g_manage_subscription_grant: dict - Dict containing properties for managing when a new subscription is granted including:
        g_eventbridge_rule_enabled: bool - If workflow is enabled or not, meaning will execute on event or not.
    g_manage_subscription_revoke: dict - Dict containing properties for managing when a subscription is revoked including:
        g_eventbridge_rule_enabled: bool - If workflow is enabled or not, meaning will execute on event or not.
"""
GOVERNANCE_WORKFLOW_PROPS = {
    'g_manage_environment_active': {        
        'g_eventbridge_rule_enabled': True
    },
    'g_manage_project_delete': {        
        'g_eventbridge_rule_enabled': True
    },
    'g_manage_subscription_grant': {        
        'g_eventbridge_rule_enabled': True
    },
    'g_manage_subscription_revoke': {        
        'g_eventbridge_rule_enabled': True
    }
}