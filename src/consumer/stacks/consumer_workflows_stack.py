from aws_cdk import (
    Stack,
    Environment
)

from constructs import Construct
from src.consumer.constructs.consumer_subscription_grant_workflow import ConsumerManageSubscriptionGrantWorkflowConstruct
from src.consumer.constructs.consumer_subscription_revoke_workflow import ConsumerManageSubscriptionRevokeWorkflowConstruct

class ConsumerWorkflowsStack(Stack):
    """ Class to represents the stack containing all consumer workflows in account."""

    def __init__(self, scope: Construct, construct_id: str, account_props: dict, workflows_props: list, common_constructs: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will deploy one of each consumer workflow constructs based on properties specified as parameter.
        
        Parameters
        ----------
        account_props : dict
            dict with common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        workflows_props : dict
            dict with required properties for all workflows creation.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        common_constructs: dic
            dict with constructs common to the account. Created in and output of account common stack.
        
        env: Environment
            Environment object with region and account details
        """
        
        super().__init__(scope, construct_id, **kwargs)
        account_id, region = account_props['account_id'], account_props['region']
        
        c_manage_subscription_grant_workflow_props = workflows_props['c_manage_subscription_grant']

        ConsumerManageSubscriptionGrantWorkflowConstruct(
            scope = self, 
            construct_id = 'dz-conn-c-manage-subscription-grant-workflow-construct',
            account_props = account_props,
            workflow_props = c_manage_subscription_grant_workflow_props,
            common_constructs = common_constructs,
            env = env
        )

        c_manage_subscription_revoke_workflow_props = workflows_props['c_manage_subscription_revoke']

        ConsumerManageSubscriptionRevokeWorkflowConstruct(
            scope = self, 
            construct_id = 'dz-conn-c-manage-subscription-revoke-workflow-construct',
            account_props = account_props,
            workflow_props = c_manage_subscription_revoke_workflow_props,
            common_constructs = common_constructs,
            env = env
        )
