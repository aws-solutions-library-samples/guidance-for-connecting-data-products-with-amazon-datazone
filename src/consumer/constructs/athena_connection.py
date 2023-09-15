from config.common.global_vars import GLOBAL_VARIABLES

from aws_cdk import (
    Environment,
    aws_athena as athena,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_sam as sam
)

from constructs import Construct

class AthenaJDBCConnectorConstruct(Construct):
    """ Class to represent an athena connection based on an underlying lambda function / application and an athena data catalog.
    It is intended to be a class to be extended per JDBC source and not deployed directly.
    """
    
    def __init__(self, scope: Construct, construct_id: str, account_props: dict, connection_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will create a lambda execution role, a lambda function / application (defined by class extending this one) and a athena data catalog.
        Resources will be created based on properties specified as parameter.
        
        Parameters
        ----------
        account_props : dict
            dict with common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        connection_props : dict
            dict with required properties for workflow creation, including:
                datazone_project_id: str - Id of the Amazon DataZone project that will be associated to the athena connection
                datazone_project_bucket_name: str - Name of the bucket assigned to the Amazon DataZone project that will be associated to the athena connection
                connection_name_suffix: str - Suffix that will be used in connection name
                host: str - Host url of the JDBC source
                port: str - Port of the JDBC source
                db_name: str - Database name of the JDBC source
                secret_name: str - Secret name with credentials of the JDBC source
                security_group_ids: list - List of security group ids to be associated to underlying lambda function / application
                subnet_ids: list - List of subnet ids where lambda function / application will be deployed
        
        env: Environment
            Environment object with region and account details
        """
        
        super().__init__(scope, construct_id, **kwargs)
        account_id, region = account_props['account_id'], account_props['region']
        
        datazone_project_id = connection_props['datazone_project_id']
        datazone_project_bucket_name = connection_props['datazone_project_bucket_name']
        connection_name_suffix = connection_props['connection_name_suffix']
        secret_name = connection_props['secret_name']
        security_group_ids = connection_props['security_group_ids']
        subnet_ids = connection_props['subnet_ids']

        connection_name = f'{datazone_project_id}-{connection_name_suffix}'
        lambda_function_name = f'{connection_name}-lambda'
        spill_bucket_arn = f"arn:aws:s3:::{datazone_project_bucket_name}"
        
        # ------------------ IAM -------------------
        connection_lambda_policy = iam.ManagedPolicy(
            scope= self,
            id= 'connection-lambda-policy',
            managed_policy_name= f'{lambda_function_name}-policy',
            statements= [
                iam.PolicyStatement(
                    actions=['s3:ListAllMyBuckets', 'athena:GetQueryExecution'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['s3:*'],
                    resources=[spill_bucket_arn, f'{spill_bucket_arn}/{lambda_function_name}/*']
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
                    actions=['secretsmanager:GetSecretValue'],
                    resources=[f'arn:aws:secretsmanager:{region}:{account_id}:secret:{secret_name}*'],
                    conditions={ 
                        'StringEquals': {
                            'aws:ResourceTag/datazone:projectId': datazone_project_id
                        }
                    }
                ),
                iam.PolicyStatement(
                    actions=['kms:Decrypt', 'kms:DescribeKey'],
                    resources=[f'arn:aws:kms:{region}:{account_id}:key/*', f'arn:aws:kms:{region}:{account_id}:alias/*']
                )
            ]
        )
        
        if not self.source_permission_boundary:
            
            connection_lambda_role = iam.Role(
                scope= self,
                id= 'connection-lambda-role',
                role_name= f'{lambda_function_name}-role',
                assumed_by= iam.ServicePrincipal('lambda.amazonaws.com')
            )

            connection_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess'))
            connection_lambda_role.add_managed_policy(connection_lambda_policy)
        
        # ------------------ Lambda -------------------
        connection_parameters = {
            'DefaultConnectionString': self.source_connection_string,
            'LambdaFunctionName': lambda_function_name,
            'SecretNamePrefix': secret_name,
            'SpillBucket': datazone_project_bucket_name,
            'SpillPrefix': lambda_function_name,
            'SecurityGroupIds': security_group_ids,
            'SubnetIds': subnet_ids
        }

        if not self.source_permission_boundary: connection_parameters['LambdaRoleARN'] = connection_lambda_role.role_arn
        else: connection_parameters['PermissionsBoundaryARN'] = connection_lambda_policy.managed_policy_arn

        athena_connector_application = sam.CfnApplication(
            scope=self,
            id='athena_connector_application',
            location=sam.CfnApplication.ApplicationLocationProperty(
                application_id= self.athena_connector_application_arn,
                semantic_version= "2023.23.1",  
            ),
            parameters=connection_parameters,
            tags= {
                'datazone:projectId': datazone_project_id
            }
        )

        connection_lambda = lambda_.Function.from_function_name(
            scope=self,
            id='connection_lambda',
            function_name=lambda_function_name
        )

        connection_lambda.node.add_dependency(athena_connector_application)

        # ---------------- Athena ----------------------
        connection_athena_data_catalog = athena.CfnDataCatalog(
            scope=self,
            id='connection_athena_data_catalog',
            name= connection_name,
            type='LAMBDA',
            parameters={
                'function': connection_lambda.function_arn
            }
        )

class AthenaMySqlJDBCConnectorConstruct(AthenaJDBCConnectorConstruct):
    """ Class to represent an MySQL athena connection based on an underlying lambda function / application and an athena data catalog."""
    
    AthenaMySQLServerlessApplicationArns = {
        'us-east-1': 'arn:aws:serverlessrepo:us-east-1:292517598671:applications/AthenaMySQLConnector'
    }
    
    def __init__(self, scope: Construct, construct_id: str, account_props: dict, connection_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will assign variables specific to MySQL, then will call super class constructor.
        For parameter definition, refer to super class description.
        """

        region = account_props['region']
        self.athena_connector_application_arn = self.AthenaMySQLServerlessApplicationArns[region]

        host = connection_props['host']
        port = connection_props['port']
        db_name = connection_props['db_name']
        secret_name = connection_props['secret_name']
        
        self.source_connection_string = f'mysql://jdbc:mysql://{host}:{port}/{db_name}?${{{secret_name}}}'
        self.source_permission_boundary = False

        super().__init__(scope, construct_id, account_props, connection_props, env, **kwargs)

class AthenaPostgresqlJDBCConnectorConstruct(AthenaJDBCConnectorConstruct):
    """ Class to represent an PostgreSQL athena connection based on an underlying lambda function / application and an athena data catalog."""

    AthenaPostgresServerlessApplicationArns = {
        'us-east-1': 'arn:aws:serverlessrepo:us-east-1:292517598671:applications/AthenaPostgreSQLConnector'
    }
    
    def __init__(self, scope: Construct, construct_id: str, account_props: dict, connection_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will assign variables specific to PostgreSQL, then will call super class constructor.
        For parameter definition, refer to super class description.
        """

        region = account_props['region']
        self.athena_connector_application_arn = self.AthenaPostgresServerlessApplicationArns[region]

        host = connection_props['host']
        port = connection_props['port']
        db_name = connection_props['db_name']
        secret_name = connection_props['secret_name']
        
        self.source_connection_string = f'postgres://jdbc:postgresql://{host}:{port}/{db_name}?${{{secret_name}}}'
        self.source_permission_boundary = False
        
        super().__init__(scope, construct_id, account_props, connection_props, env, **kwargs)

class AthenaSqlServerJDBCConnectorConstruct(AthenaJDBCConnectorConstruct):
    """ Class to represent an SQL Server athena connection based on an underlying lambda function / application and an athena data catalog."""

    AthenaSqlServerServerlessApplicationArns = {
        'us-east-1': 'arn:aws:serverlessrepo:us-east-1:292517598671:applications/AthenaSqlServerConnector'
    }
    
    def __init__(self, scope: Construct, construct_id: str, account_props: dict, connection_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will assign variables specific to SQL Server, then will call super class constructor.
        For parameter definition, refer to super class description.
        """

        region = account_props['region']
        self.athena_connector_application_arn = self.AthenaSqlServerServerlessApplicationArns[region]

        host = connection_props['host']
        port = connection_props['port']
        db_name = connection_props['db_name']
        ssl = connection_props['ssl']
        secret_name = connection_props['secret_name']
        
        self.source_connection_string = f'sqlserver://jdbc:sqlserver://{host}:{port};databaseName={db_name};encrypt={ssl};${{{secret_name}}}'
        self.source_permission_boundary = False
        
        super().__init__(scope, construct_id, account_props, connection_props, env, **kwargs)

class AthenaOracleJDBCConnectorConstruct(AthenaJDBCConnectorConstruct):
    """ Class to represent an Oracle athena connection based on an underlying lambda function / application and an athena data catalog."""

    AthenaSqlServerServerlessApplicationArns = {
        'us-east-1': 'arn:aws:serverlessrepo:us-east-1:292517598671:applications/AthenaOracleConnector'
    }
    
    def __init__(self, scope: Construct, construct_id: str, account_props: dict, connection_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will assign variables specific to Oracle, then will call super class constructor.
        For parameter definition, refer to super class description.
        """

        region = account_props['region']
        self.athena_connector_application_arn = self.AthenaSqlServerServerlessApplicationArns[region]

        host = connection_props['host']
        port = connection_props['port']
        db_name = connection_props['db_name']
        secret_name = connection_props['secret_name']
        
        self.source_connection_string = f'oracle://jdbc:oracle:thin:${{{secret_name}}}@//{host}:{port}/{db_name}'
        self.source_permission_boundary = True
        
        super().__init__(scope, construct_id, account_props, connection_props, env, **kwargs)