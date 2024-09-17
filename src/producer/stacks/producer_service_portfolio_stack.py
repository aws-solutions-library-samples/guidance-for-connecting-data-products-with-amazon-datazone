from config.common.global_vars import GLOBAL_VARIABLES
from src.producer.constructs.glue_connection import GlueJDBCConnectorConstruct, GlueJDBCConnectorWithCrawlersConstruct

from aws_cdk import (
    Stack,
    Environment,
    CfnParameter,
    aws_servicecatalog as servicecatalog,
    aws_iam as iam
)

from constructs import Construct

# ------------- Portfolio Stack ------------------------

class ProducerServicePortfolioStack(Stack):
    """ Class to represents the stack containing all producer products associated with the account service portfolio."""

    def __init__(self, scope: Construct, construct_id: str, account_props: dict, portfolio_props: dict, common_constructs: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will deploy one of each producer product in account service portfolio based on properties specified as parameter.
        Products will be assigned a specific deployment role.
        
        Parameters
        ----------
        account_props : dict
            dict with common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        portfolio_props : dict
            dict with required properties for portfolio products creation.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        common_constructs: dic
            dict with constructs common to the account. Created in and output of account common stack.
        
        env: Environment
            Environment object with region and account details
        """
        
        super().__init__(scope, construct_id, **kwargs)
        account_id, region = account_props['account_id'], account_props['region']

        # ------------------ IAM ------------------------------
        p_common_service_catalog_deploy_role = iam.Role(
            scope= self,
            id= 'p_common_servicecatalog_deploy_role',
            role_name= 'dz_conn_p_common_servicecatalog_deploy_role',
            assumed_by= iam.ServicePrincipal('servicecatalog.amazonaws.com')
        )

        p_common_service_catalog_deploy_policy = iam.ManagedPolicy(
            scope= self,
            id= 'p_common_service_catalog_deploy_role',
            managed_policy_name= 'p_common_service_catalog_deploy_role',
            statements= [
                iam.PolicyStatement(
                    actions=['s3:GetBucket', 's3:GetObject', 's3:ListBucket'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['iam:PassRole'],
                    resources=[f'arn:aws:iam::{account_id}:role/dz_conn_*']
                ),
                iam.PolicyStatement(
                    actions=['cloudformation:*'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['ec2:ModifyNetworkInterfaceAttribute', 'ec2:CreateNetworkInterface', 'ec2:DeleteNetworkInterface'],
                    resources=[f'arn:aws:ec2:{region}:{account_id}:*']
                ),
                iam.PolicyStatement(
                    actions=['ec2:DescribeVpcs', 'ec2:DescribeNetworkInterfaces', 'ec2:DescribeInternetGateways', 'ec2:DescribeAvailabilityZones', 'ec2:DescribeSubnets', 'ec2:DescribeSecurityGroups'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['glue:*Connection', 'glue:*Crawler', 'glue:TagResource'],
                    resources=[f'arn:aws:glue:{region}:{account_id}:catalog', f'arn:aws:glue:{region}:{account_id}:connection/*', f'arn:aws:glue:{region}:{account_id}:crawler/*']
                )
            ]
        )

        p_common_service_catalog_deploy_role.add_managed_policy(p_common_service_catalog_deploy_policy)

        # ------------------ Service Catalog Products ------------------------------
        a_service_portfolio = servicecatalog.Portfolio.from_portfolio_arn(
            scope= self, 
            id= 'a_service_portfolio',
            portfolio_arn= common_constructs['a_service_portfolio_arn']
        )
        
        p_glue_jdbc_connector_product = servicecatalog.CloudFormationProduct(
            scope= self, 
            id= 'p_glue_jdbc_connector_cfn_product',
            product_name='DataZone Connectors - Producer - Glue JDBC Connector', 
            owner='Data Governance Team',
            description='DataZone Connectors - Producer - Glue JDBC Connector',
            distributor='Data Governance Team',
            product_versions = [
                servicecatalog.CloudFormationProductVersion(
                    product_version_name="v1",
                    cloud_formation_template=servicecatalog.CloudFormationTemplate.from_product_stack(
                        GlueJDBCConnectorProduct(
                            scope= self, 
                            id= 'p_glue_jdbc_connector_product',
                            account_props= account_props,
                            default_props= portfolio_props['p_product_default_props']['glue_jdbc_connector'],
                            env= env
                        )
                    )
                )
            ]
        )

        a_service_portfolio.add_product(p_glue_jdbc_connector_product)
        a_service_portfolio.set_launch_role(p_glue_jdbc_connector_product, p_common_service_catalog_deploy_role)

        p_glue_jdbc_connector_crawler_product = servicecatalog.CloudFormationProduct(
            scope= self, 
            id= 'p_glue_jdbc_connector_crawler_cfn_product',
            product_name='DataZone Connectors - Producer - Glue JDBC Connector with Crawler', 
            owner='Data Governance Team',
            description='DataZone Connectors - Producer - Glue JDBC Connector with Crawler',
            distributor='Data Governance Team',
            product_versions = [
                servicecatalog.CloudFormationProductVersion(
                    product_version_name="v1",
                    cloud_formation_template=servicecatalog.CloudFormationTemplate.from_product_stack(
                        GlueJDBCConnectorWithCrawlerProduct(
                            scope= self, 
                            id= 'p_glue_jdbc_connector_crawler_product',
                            account_props= account_props,
                            default_props= portfolio_props['p_product_default_props']['glue_jdbc_connector_with_crawler'],
                            env= env
                        )
                    )
                )
            ]
        )

        a_service_portfolio.add_product(p_glue_jdbc_connector_crawler_product)
        a_service_portfolio.set_launch_role(p_glue_jdbc_connector_crawler_product, p_common_service_catalog_deploy_role)

# ------------- Portfolio Products Stacks ------------------------

class GlueJDBCConnectorBaseProduct(servicecatalog.ProductStack):
    """ Class to represents the product stack for a Glue JDBC connection.
    It is intended to be a class to be extended for products that will leverage only Glue Connection or Glue Connection plus Glue Crawler.
    """

    def __init__(self, scope: Construct, id: str, account_props: dict, default_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will define product input parameters. Actual resources will be defined by classes extending this one.
        
        Parameters
        ----------
        account_props : dict
            dict with common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        default_props : dict
            dict with default properties for product parameters.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.
        
        env: Environment
            Environment object with region and account details
        """
        
        super().__init__(scope, id, **kwargs)

        # ------------- Parameters --------------------
        p_datazone_domain_id_param = CfnParameter(
            scope= self,
            id= 'DataZoneDomainId',
            description= 'Id of the Amazon DataZone domain where project belongs' 
        )

        p_datazone_project_id_param = CfnParameter(
            scope= self,
            id= 'DataZoneProjectId',
            description= 'Id of the Amazon DataZone project from which connector will be accessed' 
        )

        p_datazone_environment_id_param = CfnParameter(
            scope= self,
            id= 'DataZoneEnvironmentId',
            description= 'Id of the Amazon DataZone environment from which connector will be accessed' 
        )
        
        p_connection_name_param = CfnParameter(
            scope= self,
            id= 'ConnectionName',
            description= 'Name to assign to the connection' 
        )
        
        p_engine_param = CfnParameter(
            scope= self,
            id= 'ConnectionSourceEngine',
            description= 'Id of the Amazon DataZone environment from which connector will be accessed' 
        )

        p_host_param = CfnParameter(
            scope= self,
            id= 'ConnectionSourceHost',
            description= 'Host of the JDBC source you will be connecting to.'
        )

        p_port_param = CfnParameter(
            scope= self,
            id= 'ConnectionSourcePort',
            description= 'Port of the JDBC source you will be connecting to.'
        )

        p_db_name_param = CfnParameter(
            scope= self,
            id= 'ConnectionSourceDatabaseName',
            description= 'Name of the database from the JDBC source you will be connecting to.'
        )

        p_secret_arn_suffix_param = CfnParameter(
            scope= self,
            id= 'ConnectionSecretArnSuffix',
            description= 'Name of the secret with credentials of the JDBC source you will be connecting to.'
        )

        p_ssl_param = CfnParameter(
            scope= self,
            id= 'ConnectionSSL',
            description= 'If connection needs to enforce ssl ("True" or "False").',
            default = str(default_props['ssl'])
        )

        p_availability_zone_param = CfnParameter(
            scope= self,
            id= 'ConnectionVpcAvailabilityZone',
            description= 'Availability Zone to apply to Glue connection that allows connection to JDBC source.',
            default = default_props['availability_zone']
        )

        p_security_group_ids_param = CfnParameter(
            scope= self,
            id= 'ConnectionVpcSecurityGroupIds',
            description= 'Security group ids to apply to Glue connection that allows connection to JDBC source.',
            default = ','.join(default_props['security_group_ids'])
        )

        p_subnet_id_param = CfnParameter(
            scope= self,
            id= 'ConnectionVpcSubnetId',
            description= 'Subnet ids to deploy Glue connection in, that allows connection to JDBC source.',
            default = default_props['subnet_id']
        )

        # -------------- Consolidated Parameters -------------------
        self.p_connection_props = {
            'datazone_domain_id': p_datazone_domain_id_param.value_as_string,
            'datazone_project_id': p_datazone_project_id_param.value_as_string,
            'datazone_environment_id': p_datazone_environment_id_param.value_as_string,
            'glue_connection': {
                'name': p_connection_name_param.value_as_string,
                'engine': p_engine_param.value_as_string,
                'host': p_host_param.value_as_string,
                'port': p_port_param.value_as_string,
                'db_name': p_db_name_param.value_as_string,
                'secret_arn_suffix': p_secret_arn_suffix_param.value_as_string,
                'ssl': p_ssl_param.value_as_string,
                'availability_zone': p_availability_zone_param.value_as_string,
                'security_group_ids': p_security_group_ids_param.value_as_string,
                'subnet_id': p_subnet_id_param.value_as_string
            }
        }

class GlueJDBCConnectorProduct(GlueJDBCConnectorBaseProduct):
    """ Class to represents the product stack for a Glue JDBC connection."""

    def __init__(self, scope: Construct, id: str, account_props: dict, default_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will call super class constructor to define product input parameters. Will define actual resources to be deployed.
        For parameter definition, refer to super class description.
        """
        
        super().__init__(scope, id, account_props, default_props, env, **kwargs)

        # -------------- Product -------------------
        p_glue_jdbc_connector_construct = GlueJDBCConnectorConstruct(
            scope= self,
            construct_id= 'p_glue_jdbc_connector_construct',
            account_props= account_props,
            connection_props = self.p_connection_props,
            env= env
        )

class GlueJDBCConnectorWithCrawlerProduct(GlueJDBCConnectorBaseProduct):
    """ Class to represents the product stack for a Glue JDBC connection with a single associated Glue crawler."""

    def __init__(self, scope: Construct, id: str, account_props: dict, default_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will call super class constructor to define product input parameters and include new ones. Will also define actual resources to be deployed.
        For parameter definition, refer to super class description.
        """
        
        super().__init__(scope, id, account_props, default_props, env, **kwargs)

        # ------------- Parameters --------------------
        p_crawler_name_param = CfnParameter(
            scope= self,
            id= 'CrawlerName',
            description= 'Name to assign to the Glue crawler' 
        )

        p_catalog_db_name_param = CfnParameter(
            scope= self,
            id= 'CrawlerCatalogDatabaseName',
            description= 'Name of the target Glue database name' 
        )

        p_table_prefix_param = CfnParameter(
            scope= self,
            id= 'CrawlerTablePrefix',
            description= 'Table prefix to consider by the Glue crawler' 
        )

        p_source_db_path_param = CfnParameter(
            scope= self,
            id= 'CrawlerSourceDatabasePath',
            description= 'Path from within source database to crawl by Glue crawler' 
        )

        # -------------- Consolidated Parameters -------------------
        self.p_connection_props['glue_crawlers'] = {
            'connection_glue_crawler': {
                'name': p_crawler_name_param.value_as_string,
                'catalog_database_name': p_catalog_db_name_param.value_as_string,
                'table_prefix': p_table_prefix_param.value_as_string,
                'source_db_path': p_source_db_path_param.value_as_string
            }
        }
        
        # -------------- Product -------------------
        p_glue_jdbc_connector_crawler_construct = GlueJDBCConnectorWithCrawlersConstruct(
            scope= self,
            construct_id= 'p_glue_jdbc_connector_crawler_construct',
            account_props= account_props,
            connection_props = self.p_connection_props,
            env= env
        )

