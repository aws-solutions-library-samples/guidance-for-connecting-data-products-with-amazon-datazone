#!/usr/bin/env python3
import aws_cdk as cdk
from importlib import import_module

from src.account.stacks.account_common_stack import DataZoneConnectorsAccountCommonStack

from src.producer.stacks.producer_common_stack import DataZoneConnectorsProducerCommonStack
from src.producer.stacks.producer_workflows_stack import ProducerWorkflowsStack
from src.producer.stacks.producer_service_portfolio_stack import ProducerServicePortfolioStack

from src.consumer.stacks.consumer_workflows_stack import ConsumerWorkflowsStack
from src.consumer.stacks.consumer_service_portfolio_stack import ConsumerServicePortfolioStack

app = cdk.App()
account = cdk.Aws.ACCOUNT_ID
region = cdk.Aws.REGION

env = cdk.Environment(
    account= account,
    region= region
)

context_account_id = app.node.try_get_context("account")
account_config_module = import_module(f'config.account.a_{context_account_id}_config')

ACCOUNT_PROPS = getattr(account_config_module, 'ACCOUNT_PROPS')

PRODUCER_PROPS = getattr(account_config_module, 'PRODUCER_PROPS')
PRODUCER_WORKFLOW_PROPS = getattr(account_config_module, 'PRODUCER_WORKFLOW_PROPS')
PRODUCER_SERVICE_PORTFOLIO_PROPS = getattr(account_config_module, 'PRODUCER_SERVICE_PORTFOLIO_PROPS')

CONSUMER_WORKFLOW_PROPS = getattr(account_config_module, 'CONSUMER_WORKFLOW_PROPS')
CONSUMER_SERVICE_PORTFOLIO_PROPS = getattr(account_config_module, 'CONSUMER_SERVICE_PORTFOLIO_PROPS')


# ---------------- Account Stacks ------------------------
account_common_constructs = {}

dz_conn_a_common_stack = DataZoneConnectorsAccountCommonStack(
    scope= app,
    construct_id = "dz-conn-a-common-stack",
    account_props = ACCOUNT_PROPS,
    env = env
)

account_common_constructs = {
    **account_common_constructs,
    **dz_conn_a_common_stack.outputs
}

# ---------------- Producer Stacks ------------------------
dz_conn_p_common_stack = DataZoneConnectorsProducerCommonStack(
    scope= app,
    construct_id = "dz-conn-p-common-stack",
    account_props = ACCOUNT_PROPS,
    producer_props = PRODUCER_PROPS,
    common_constructs = account_common_constructs,
    env = env
)

dz_conn_p_common_stack.node.add_dependency(dz_conn_a_common_stack)

account_common_constructs = {
    **account_common_constructs,
    **dz_conn_p_common_stack.outputs
}

dz_conn_p_workflows_stack = ProducerWorkflowsStack(
    scope= app,
    construct_id = "dz-conn-p-workflows-stack",
    account_props = ACCOUNT_PROPS,
    workflows_props = PRODUCER_WORKFLOW_PROPS,
    common_constructs = account_common_constructs,
    env = env
)

dz_conn_p_service_portfolio_stack =  ProducerServicePortfolioStack(
    scope= app,
    construct_id = "dz-conn-p-service-portfolio-stack",
    account_props = ACCOUNT_PROPS,
    portfolio_props = PRODUCER_SERVICE_PORTFOLIO_PROPS,
    common_constructs = account_common_constructs,
    env = env
)

# ---------------- Consumer Stacks ------------------------
dz_conn_c_workflows_stack = ConsumerWorkflowsStack(
    scope= app,
    construct_id = "dz-conn-c-workflows-stack",
    account_props = ACCOUNT_PROPS,
    workflows_props = CONSUMER_WORKFLOW_PROPS,
    common_constructs = account_common_constructs,
    env = env
)

dz_conn_c_service_portfolio_stack =  ConsumerServicePortfolioStack(
    scope= app,
    construct_id = "dz-conn-c-service-portfolio-stack",
    account_props = ACCOUNT_PROPS,
    portfolio_props = CONSUMER_SERVICE_PORTFOLIO_PROPS,
    common_constructs = account_common_constructs,
    env = env
)

app.synth()
