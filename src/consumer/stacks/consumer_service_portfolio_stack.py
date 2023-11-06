from config.common.global_vars import GLOBAL_VARIABLES
from src.consumer.constructs.athena_connection import AthenaMySqlJDBCConnectorConstruct, AthenaPostgresqlJDBCConnectorConstruct, AthenaSqlServerJDBCConnectorConstruct, AthenaOracleJDBCConnectorConstruct

from aws_cdk import (
    Stack,
    Environment,
    CfnParameter,
    aws_servicecatalog as servicecatalog,
    aws_iam as iam
)

from constructs import Construct

# ------------- Portfolio Stack ------------------------

class ConsumerServicePortfolioStack(Stack):
    """ Class to represents the stack containing all consumer products associated with the account service portfolio."""

    def __init__(self, scope: Construct, construct_id: str, account_props: dict, portfolio_props: dict, common_constructs: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will deploy one of each consumer product in account service portfolio based on properties specified as parameter.
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
        c_common_service_catalog_deploy_role = iam.Role(
            scope= self,
            id= 'c_common_servicecatalog_deploy_role',
            role_name= 'dz_conn_c_common_servicecatalog_deploy_role',
            assumed_by= iam.ServicePrincipal('servicecatalog.amazonaws.com')
        )

        c_common_service_catalog_deploy_policy = iam.ManagedPolicy(
            scope= self,
            id= 'c_common_service_catalog_deploy_role',
            managed_policy_name= 'c_common_service_catalog_deploy_role',
            statements= [
                iam.PolicyStatement(
                    actions=['s3:GetBucket', 's3:GetObject', 's3:ListBucket'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['iam:*Role', 'iam:List*', 'iam:*RolePolicy', 'iam:*Policy*'],
                    resources=[f'arn:aws:iam::{account_id}:role/*', f'arn:aws:iam::{account_id}:policy/*']
                ),
                iam.PolicyStatement(
                    actions=['cloudformation:*', 'serverlessrepo:*CloudFormation*'],
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
                    actions=['lambda:*Function', 'lambda:TagResource', 'lambda:UntagResource'],
                    resources=[f'arn:aws:lambda:{region}:{account_id}:function:*']
                ),
                iam.PolicyStatement(
                    actions=['athena:*DataCatalog'],
                    resources=[f'arn:aws:athena:{region}:{account_id}:datacatalog/*']
                )
            ]
        )

        c_common_service_catalog_deploy_role.add_managed_policy(c_common_service_catalog_deploy_policy)
        
        # ------------------ Service Catalog Products ------------------------------
        a_service_portfolio = servicecatalog.Portfolio.from_portfolio_arn(
            scope= self, 
            id= 'a_service_portfolio',
            portfolio_arn= common_constructs['a_service_portfolio_arn']
        )
        
        c_athena_mysql_jdbc_connector_product = servicecatalog.CloudFormationProduct(
            scope= self, 
            id= 'c_athena_mysql_jdbc_connector_cfn_product',
            product_name='DataZone Connectors - Consumer - Athena MySQL JDBC Connector', 
            owner='Data Governance Team',
            description='DataZone Connectors - Consumer - Athena MySQL JDBC Connector',
            distributor='Data Governance Team',
            product_versions = [
                servicecatalog.CloudFormationProductVersion(
                    product_version_name="v1",
                    cloud_formation_template=servicecatalog.CloudFormationTemplate.from_product_stack(
                        AthenaMySqlJDBCConnectorProduct(
                            scope= self, 
                            id= 'c_athena_mysql_jdbc_connector_product',
                            account_props= account_props,
                            default_props= portfolio_props['c_product_default_props']['athena_mysql_jdbc_connector'],
                            env= env
                        )
                    )
                )
            ]
        )

        a_service_portfolio.add_product(c_athena_mysql_jdbc_connector_product)
        a_service_portfolio.set_launch_role(c_athena_mysql_jdbc_connector_product, c_common_service_catalog_deploy_role)
        
        c_athena_postgres_jdbc_connector_product = servicecatalog.CloudFormationProduct(
            scope= self, 
            id= 'c_athena_postgres_jdbc_connector_cfn_product',
            product_name='DataZone Connectors - Consumer - Athena PostgreSQL JDBC Connector', 
            owner='Data Governance Team',
            description='DataZone Connectors - Consumer - Athena PostgreSQL JDBC Connector',
            distributor='Data Governance Team',
            product_versions = [
                servicecatalog.CloudFormationProductVersion(
                    product_version_name="v1",
                    cloud_formation_template=servicecatalog.CloudFormationTemplate.from_product_stack(
                        AthenaPostgresJDBCConnectorProduct(
                            scope= self, 
                            id= 'c_athena_postgres_jdbc_connector_product',
                            account_props= account_props,
                            default_props= portfolio_props['c_product_default_props']['athena_postgres_jdbc_connector'],
                            env= env
                        )
                    )
                )
            ]
        )

        a_service_portfolio.add_product(c_athena_postgres_jdbc_connector_product)
        a_service_portfolio.set_launch_role(c_athena_postgres_jdbc_connector_product, c_common_service_catalog_deploy_role)

        c_athena_sqlserver_jdbc_connector_product = servicecatalog.CloudFormationProduct(
            scope= self, 
            id= 'c_athena_sqlserver_jdbc_connector_cfn_product',
            product_name='DataZone Connectors - Consumer - Athena SQL Server JDBC Connector', 
            owner='Data Governance Team',
            description='DataZone Connectors - Consumer - Athena SQL Server JDBC Connector',
            distributor='Data Governance Team',
            product_versions = [
                servicecatalog.CloudFormationProductVersion(
                    product_version_name="v1",
                    cloud_formation_template=servicecatalog.CloudFormationTemplate.from_product_stack(
                        AthenaSqlServerJDBCConnectorProduct(
                            scope= self, 
                            id= 'c_athena_sqlserver_jdbc_connector_product',
                            account_props= account_props,
                            default_props= portfolio_props['c_product_default_props']['athena_sqlserver_jdbc_connector'],
                            env= env
                        )
                    )
                )
            ]
        )

        a_service_portfolio.add_product(c_athena_sqlserver_jdbc_connector_product)
        a_service_portfolio.set_launch_role(c_athena_sqlserver_jdbc_connector_product, c_common_service_catalog_deploy_role)

        c_athena_oracle_jdbc_connector_product = servicecatalog.CloudFormationProduct(
            scope= self, 
            id= 'c_athena_oracle_jdbc_connector_cfn_product',
            product_name='DataZone Connectors - Consumer - Athena Oracle JDBC Connector', 
            owner='Data Governance Team',
            description='DataZone Connectors - Consumer - Athena Oracle JDBC Connector',
            distributor='Data Governance Team',
            product_versions = [
                servicecatalog.CloudFormationProductVersion(
                    product_version_name="v1",
                    cloud_formation_template=servicecatalog.CloudFormationTemplate.from_product_stack(
                        AthenaOracleJDBCConnectorProduct(
                            scope= self, 
                            id= 'c_athena_oracle_jdbc_connector_product',
                            account_props= account_props,
                            default_props= portfolio_props['c_product_default_props']['athena_oracle_jdbc_connector'],
                            env= env
                        )
                    )
                )
            ]
        )

        a_service_portfolio.add_product(c_athena_oracle_jdbc_connector_product)
        a_service_portfolio.set_launch_role(c_athena_oracle_jdbc_connector_product, c_common_service_catalog_deploy_role)

# ------------- Portfolio Products Stacks ------------------------

class AthenaJDBCConnectorProduct(servicecatalog.ProductStack):
    """ Class to represents the product stack for an Athena JDBC connection. 
    It is intended to be a class to be extended per JDBC source and not deployed directly.
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
        c_connection_name_suffix_param = CfnParameter(
            scope= self,
            id= 'ConnectionNameSuffix',
            description= 'Name suffix to include in the connection name' 
        )

        c_datazone_domain_id_param = CfnParameter(
            scope= self,
            id= 'DataZoneDomainId',
            description= 'Id of the Amazon DataZone domain where project belongs' 
        )
        
        c_datazone_project_id_param = CfnParameter(
            scope= self,
            id= 'DataZoneProjectId',
            description= 'Id of the Amazon DataZone project from which connector will be accessed' 
        )

        c_datazone_environment_id_param = CfnParameter(
            scope= self,
            id= 'DataZoneEnvironmentId',
            description= 'Id of the Amazon DataZone environment from which connector will be accessed' 
        )

        c_host_param = CfnParameter(
            scope= self,
            id= 'ConnectionSourceHost',
            description= 'Host of the JDBC source you will be connecting to.'
        )

        c_port_param = CfnParameter(
            scope= self,
            id= 'ConnectionSourcePort',
            description= 'Port of the JDBC source you will be connecting to.',
            default = default_props['port']
        )

        c_db_name_param = CfnParameter(
            scope= self,
            id= 'ConnectionSourceDatabaseName',
            description= 'Name of the database from the JDBC source you will be connecting to.'
        )

        c_secret_name_param = CfnParameter(
            scope= self,
            id= 'ConnectionSecretName',
            description= 'Name of the secret with credentials of the JDBC source you will be connecting to.'
        )

        c_security_group_ids_param = CfnParameter(
            scope= self,
            id= 'ConnectionVpcSecurityGroupIds',
            description= 'Security group ids to apply to Athena connector that allows connection to JDBC source.',
            default = ','.join(default_props['security_group_ids'])
        )

        c_subnet_ids_param = CfnParameter(
            scope= self,
            id= 'ConnectionVpcSubnetIds',
            description= 'Subnet ids to deploy Athena connector in, that allows connection to JDBC source.',
            default = ','.join(default_props['subnet_ids'])
        )

        # -------------- Consolidated Parameters -------------------
        self.c_connection_props = {
            'connection_name_suffix': c_connection_name_suffix_param.value_as_string,
            'datazone_domain_id': c_datazone_domain_id_param.value_as_string,
            'datazone_project_id': c_datazone_project_id_param.value_as_string,
            'datazone_environment_id': c_datazone_environment_id_param.value_as_string,
            'host': c_host_param.value_as_string,
            'port': c_port_param.value_as_string,
            'db_name': c_db_name_param.value_as_string,
            'secret_name': c_secret_name_param.value_as_string,
            'security_group_ids': c_security_group_ids_param.value_as_string,
            'subnet_ids': c_subnet_ids_param.value_as_string
        }

class AthenaMySqlJDBCConnectorProduct(AthenaJDBCConnectorProduct):
    """ Class to represents the product stack for an Athena MySQL JDBC connection."""

    def __init__(self, scope: Construct, id: str, account_props: dict, default_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will call super class constructor to define product input parameters. Will define actual resources to be deployed.
        For parameter definition, refer to super class description.
        """

        super().__init__(scope, id, account_props, default_props, env, **kwargs)

        c_athena_mysql_jdbc_connector_construct = AthenaMySqlJDBCConnectorConstruct(
            scope= self,
            construct_id= 'c_athena_mysql_jdbc_connector_construct',
            account_props= account_props,
            connection_props = self.c_connection_props,
            env= env
        )

class AthenaPostgresJDBCConnectorProduct(AthenaJDBCConnectorProduct):
    """ Class to represents the product stack for an Athena PostgreSQL JDBC connection."""

    def __init__(self, scope: Construct, id: str, account_props: dict, default_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will call super class constructor to define product input parameters. Will define actual resources to be deployed.
        For parameter definition, refer to super class description.
        """
        
        super().__init__(scope, id, account_props, default_props, env, **kwargs)

        c_athena_postgres_jdbc_connector_construct = AthenaPostgresqlJDBCConnectorConstruct(
            scope= self,
            construct_id= 'c_athena_postgres_jdbc_connector_construct',
            account_props= account_props,
            connection_props = self.c_connection_props,
            env= env
        )

class AthenaSqlServerJDBCConnectorProduct(AthenaJDBCConnectorProduct):
    """ Class to represents the product stack for an Athena SQL Server JDBC connection."""

    def __init__(self, scope: Construct, id: str, account_props: dict, default_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will call super class constructor to define product input parameters. Will define actual resources to be deployed.
        For parameter definition, refer to super class description.
        """
        
        super().__init__(scope, id, account_props, default_props, env, **kwargs)

        # ------------- Parameters --------------------
        # c_ssl_param = CfnParameter(
        #     scope= self,
        #     id= 'ConnectionSsl',
        #     description= 'If connection to source database should use SSL',
        #     default = default_props['ssl']
        # )

        # -------------- Consolidated Parameters -------------------
        # self.c_connection_props = {
        #     **self.c_connection_props,
        #     'ssl': c_ssl_param.value_as_string
        # }
        
        c_athena_sqlserver_jdbc_connector_construct = AthenaSqlServerJDBCConnectorConstruct(
            scope= self,
            construct_id= 'c_athena_sqlserver_jdbc_connector_construct',
            account_props= account_props,
            connection_props = self.c_connection_props,
            env= env
        )

class AthenaOracleJDBCConnectorProduct(AthenaJDBCConnectorProduct):
    """ Class to represents the product stack for an Athena Oracle JDBC connection."""

    def __init__(self, scope: Construct, id: str, account_props: dict, default_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will call super class constructor to define product input parameters. Will define actual resources to be deployed.
        For parameter definition, refer to super class description.
        """
        
        super().__init__(scope, id, account_props, default_props, env, **kwargs)
        
        c_athena_oracle_jdbc_connector_construct = AthenaOracleJDBCConnectorConstruct(
            scope= self,
            construct_id= 'c_athena_oracle_jdbc_connector_construct',
            account_props= account_props,
            connection_props = self.c_connection_props,
            env= env
        )

