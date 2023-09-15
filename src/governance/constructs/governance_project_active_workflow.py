from config.common.global_vars import GLOBAL_VARIABLES

from aws_cdk import (
    Environment,
    aws_stepfunctions as stepfunctions,
    aws_events as events,
    aws_events_targets as event_targets,
    aws_iam as iam
)

from constructs import Construct

class GovernanceManageProjectActiveWorkflowConstruct(Construct):
    """ Class to represent the workflow that will execute after a Amazon DataZone project is turned active.
    The workflow will update project roles' permission boundaries and policies. Additionally will assign LF-tags to project Glue catalog databases.
    Actions will be performed in account owning the Amazon DataZone Project through cross-account access.
    """
    
    def __init__(self, scope: Construct, construct_id: str, governance_props: dict, workflow_props: dict, common_constructs: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will create a workflow (state machine and event rule/target) based on properties specified as parameter
        Lambdas to be invoked by the workflow are provisioned in account common stack.
        
        Parameters
        ----------
        governance_props : dict
            dict with common properties for governance account.
            For more details check config/governance/g_config.py documentation and examples.

        workflow_props : dict
            dict with required properties for workflow creation.
            For more details check config/governance/g_config.py documentation and examples.

        common_constructs: dic
            dict with constructs common to the governance account. Created in and output of governance common stack.
        
        env: Environment
            Environment object with region and account details
        """

        super().__init__(scope, construct_id, **kwargs)
        account_id, region = governance_props['account_id'], governance_props['region']
        
        # ---------------- Step Functions ------------------------    
        g_manage_project_active_state_machine = stepfunctions.StateMachine(
            scope= self,
            id= 'g_manage_project_active_state_machine',
            state_machine_name= 'dz_conn_g_manage_project_active',
            definition_body=stepfunctions.DefinitionBody.from_file('src/governance/code/stepfunctions/governance_manage_project_active_workflow.asl.json'),
            definition_substitutions= {
                'region': region,
                'a_update_project_roles_lambda_name': GLOBAL_VARIABLES['account']['a_update_project_roles_lambda_name'],
                'p_add_lf_tag_project_dbs_lambda_name': GLOBAL_VARIABLES['producer']['p_add_lf_tag_project_dbs_lambda_name'],
                'a_cross_account_assume_role_name': GLOBAL_VARIABLES['account']['a_cross_account_assume_role_name'],
            },
            role=common_constructs['g_common_sf_role']
        )

        # --------------- EventBridge ---------------------------
        g_common_eventbridge_role = iam.Role.from_role_name(
            scope= self, 
            id= 'g_common_eventbridge_role_name',
            role_name= common_constructs['g_common_eventbridge_role_name']
        )
        
        g_manage_project_active_rule = events.Rule(
            scope= self,
            id= 'g_manage_project_active_rule',
            rule_name= 'dz_conn_g_manage_project_active_rule',
            enabled=workflow_props['g_eventbridge_rule_enabled'],
            event_pattern=events.EventPattern(
                source=['aws.datazone'],
                detail_type=['Data Project Update'],
                detail={
                    'message': ['ACTIVE']
                }
            )
        )

        g_manage_project_active_rule_target = event_targets.SfnStateMachine(
            machine= g_manage_project_active_state_machine,
            role=g_common_eventbridge_role,
            input=events.RuleTargetInput.from_object(
                { 'EventDetails': events.EventField.from_path('$.detail') }
            )
        )

        g_manage_project_active_rule.add_target(g_manage_project_active_rule_target)

