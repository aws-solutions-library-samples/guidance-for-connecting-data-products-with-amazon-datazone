#!/usr/bin/env python3
import aws_cdk as cdk

from config.governance.g_config import GOVERNANCE_PROPS, GOVERNANCE_WORKFLOW_PROPS

from src.governance.stacks.governance_common_stack import DataZoneConnectorsGovernanceCommonStack
from src.governance.stacks.governance_workflows_stack import GovernanceWorkflowsStack

app = cdk.App()
account = cdk.Aws.ACCOUNT_ID
region = cdk.Aws.REGION

env = cdk.Environment(
    account= account,
    region= region
)

# ---------------- Governance Stacks ------------------------
governance_common_constructs = {}

dz_conn_g_common_stack = DataZoneConnectorsGovernanceCommonStack(
    scope= app,
    construct_id = "dz-conn-g-common-stack",
    governance_props = GOVERNANCE_PROPS,
    env = env
)

governance_common_constructs = {
    **governance_common_constructs,
    **dz_conn_g_common_stack.outputs
}

dz_conn_g_workflows_stack = GovernanceWorkflowsStack(
    scope= app,
    construct_id = "dz-conn-g-workflows-stack",
    governance_props = GOVERNANCE_PROPS,
    workflows_props = GOVERNANCE_WORKFLOW_PROPS,
    common_constructs = governance_common_constructs,
    env = env
)

app.synth()
