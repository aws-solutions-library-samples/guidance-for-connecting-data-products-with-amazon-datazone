from aws_cdk import (
    Stack
)

from constructs import Construct
from src.producer.constructs.producer_subscription_grant_workflow import ProducerManageSubscriptionGrantWorkflowConstruct
from src.producer.constructs.producer_subscription_revoke_workflow import ProducerManageSubscriptionRevokeWorkflowConstruct

class ProducerWorkflowsStack(Stack):
    """ Class to represents the stack containing all producer workflows in account."""

    def __init__(self, scope: Construct, construct_id: str, account_props: dict, workflows_props: list, common_constructs: dict, **kwargs) -> None:
        """ Class Constructor. Will deploy one of each producer workflow constructs based on properties specified as parameter.
        
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

        env = kwargs.get('env')
        
        p_manage_subscription_grant_workflow_props = workflows_props['p_manage_subscription_grant']

        ProducerManageSubscriptionGrantWorkflowConstruct(
            scope = self, 
            construct_id = 'dz-conn-p-manage-subscription-grant-workflow-construct',
            account_props = account_props,
            workflow_props = p_manage_subscription_grant_workflow_props,
            common_constructs = common_constructs,
            env = env
        )

        p_manage_subscription_revoke_workflow_props = workflows_props['p_manage_subscription_revoke']

        ProducerManageSubscriptionRevokeWorkflowConstruct(
            scope = self, 
            construct_id = 'dz-conn-p-manage-subscription-revoke-workflow-construct',
            account_props = account_props,
            workflow_props = p_manage_subscription_revoke_workflow_props,
            common_constructs = common_constructs,
            env = env
        )
