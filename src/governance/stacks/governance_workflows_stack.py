from aws_cdk import (
    Stack,
    Environment
)

from constructs import Construct
from src.governance.constructs.governance_environment_active_workflow import GovernanceManageEnvironmentActiveWorkflowConstruct
from src.governance.constructs.governance_environment_delete_workflow import GovernanceManageEnvironmentDeleteWorkflowConstruct
from src.governance.constructs.governance_subscription_grant_workflow import GovernanceManageSubscriptionGrantWorkflowConstruct
from src.governance.constructs.governance_subscription_revoke_workflow import GovernanceManageSubscriptionRevokeWorkflowConstruct

class GovernanceWorkflowsStack(Stack):
    """ Class to represents the stack containing all workflows in governance account."""

    def __init__(self, scope: Construct, construct_id: str, governance_props: dict, workflows_props: list, common_constructs: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will deploy one of each governance workflow constructs based on properties specified as parameter.
        
        Parameters
        ----------
        governance_props : dict
            dict with common properties for governance account.
            For more details check config/governance/g_config.py documentation and examples.

        workflows_props : dict
            dict with required properties for all workflows creation.
            For more details check config/governance/g_config.py documentation and examples.

        common_constructs: dic
            dict with constructs common to the governance account. Created in and output of governance common stack.
        
        env: Environment
            Environment object with region and account details
        """

        super().__init__(scope, construct_id, **kwargs)
        account_id, region = governance_props['account_id'], governance_props['region']
        
        g_manage_environment_active_workflow_props = workflows_props['g_manage_environment_active']

        GovernanceManageEnvironmentActiveWorkflowConstruct(
            scope = self, 
            construct_id = 'dz-conn-g-manage-environment-active-workflow-construct',
            governance_props = governance_props,
            workflow_props = g_manage_environment_active_workflow_props,
            common_constructs = common_constructs,
            env = env
        )

        g_manage_environment_delete_workflow_props = workflows_props['g_manage_environment_delete']

        GovernanceManageEnvironmentDeleteWorkflowConstruct(
            scope = self, 
            construct_id = 'dz-conn-g-manage-environment-delete-workflow-construct',
            governance_props = governance_props,
            workflow_props = g_manage_environment_delete_workflow_props,
            common_constructs = common_constructs,
            env = env
        )
        
        g_manage_subscription_grant_workflow_props = workflows_props['g_manage_subscription_grant']

        GovernanceManageSubscriptionGrantWorkflowConstruct(
            scope = self, 
            construct_id = 'dz-conn-g-manage-subscription-grant-workflow-construct',
            governance_props = governance_props,
            workflow_props = g_manage_subscription_grant_workflow_props,
            common_constructs = common_constructs,
            env = env
        )

        g_manage_subscription_revoke_workflow_props = workflows_props['g_manage_subscription_revoke']

        GovernanceManageSubscriptionRevokeWorkflowConstruct(
            scope = self, 
            construct_id = 'dz-conn-g-manage-subscription-revoke-workflow-construct',
            governance_props = governance_props,
            workflow_props = g_manage_subscription_revoke_workflow_props,
            common_constructs = common_constructs,
            env = env
        )
