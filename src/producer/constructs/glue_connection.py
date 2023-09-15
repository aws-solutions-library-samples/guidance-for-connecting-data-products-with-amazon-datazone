from config.common.global_vars import GLOBAL_VARIABLES

from aws_cdk import (
    Environment,
    Tags,
    aws_glue as glue
)

from constructs import Construct

class GlueJDBCConnectorConstruct(Construct):
    """ Class to represent a glue connection for JDBC sources."""

    def __init__(self, scope: Construct, construct_id: str, account_props: dict, connection_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will create a JDBC glue connection.
        Resources will be created based on properties specified as parameter.
        
        Parameters
        ----------
        account_props : dict
            dict with common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        connection_props : dict
            dict with required properties for workflow creation, including:
                datazone_project_id: str - Id of the Amazon DataZone project that will be associated to the glue connection
                glue_connection: dict - Dict containing connection specific properties including:
                    name: str - Name to assign to the glue connection.
                    engine: str - Engine of the JDBC source
                    host: str - Host url of the JDBC source
                    port: str - Port of the JDBC source
                    db_name: str - Database name of the JDBC source
                    ssl: str - 'True' or 'False' depending if ssl needs to be enforced by connection
                    secret_arn_suffix: str - Secret arn suffix with credentials of admin user of the JDBC source. Note that is not the name but the id as specified in ARN.
                    availability_zone: str - Availability zone where glue connection will be connecting from
                    security_group_ids: list - List of security group ids to be associated to the glue connection
                    subnet_id: str - Subnet id where glue connection will be connecting from
        
        env: Environment
            Environment object with region and account details
        """

        super().__init__(scope, construct_id, **kwargs)
        account_id, region = account_props['account_id'], account_props['region']

        datazone_project_id = connection_props['datazone_project_id']
        glue_connection_props = connection_props['glue_connection']
        glue_connection_engine = glue_connection_props['engine']
        glue_connection_host = glue_connection_props['host']
        glue_connection_port = glue_connection_props['port']
        glue_connection_db_name = glue_connection_props['db_name']
        glue_connection_ssl = glue_connection_props['ssl']


        glue_connection_jdbc_url = f'jdbc:{glue_connection_engine}://{glue_connection_host}:{glue_connection_port}/{glue_connection_db_name}'
        glue_connection_secret_arn_suffix = glue_connection_props['secret_arn_suffix']
        glue_connection_secret_arn = f'arn:aws:secretsmanager:{region}:{account_id}:secret:{glue_connection_secret_arn_suffix}'
        
        self.glue_connection = glue.CfnConnection(
            scope= self, 
            id= 'glue_connection',
            catalog_id= account_id,
            connection_input=glue.CfnConnection.ConnectionInputProperty(
                name= glue_connection_props["name"],
                connection_type= 'JDBC',

                connection_properties= {
                    'JDBC_CONNECTION_URL': glue_connection_jdbc_url,
                    'SECRET_ID': glue_connection_secret_arn,
                    'JDBC_ENFORCE_SSL': glue_connection_ssl
                },

                physical_connection_requirements= glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                    availability_zone= glue_connection_props["availability_zone"],
                    security_group_id_list= glue_connection_props["security_group_ids"].split(','),
                    subnet_id= glue_connection_props["subnet_id"]
                )
            )
        )

        Tags.of(self.glue_connection).add('datazone:projectId', datazone_project_id)


class GlueJDBCConnectorWithCrawlersConstruct(GlueJDBCConnectorConstruct):
    """ Class to represent a glue connection for JDBC sources with a set of Glue crawlers associated to it.
    Extends glue connection construct.
    """

    def __init__(self, scope: Construct, construct_id: str, account_props: dict, connection_props: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will create a JDBC glue connection.
        Resources will be created based on properties specified as parameter.
        
        Parameters
        ----------
        account_props : dict
            dict with common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        connection_props : dict
            dict with required properties for workflow creation, including:
                datazone_project_id: str - Id of the Amazon DataZone project that will be associated to the glue connection
                glue_connection: dict - Dict containing connection specific properties (refer to super class for more details)
                glue_crawlers: list - List containing a list of dicts, each with properties of a crawler to associate to the connection, including:
                    name: str - Name to assign to the glue crawler.
                    catalog_database_name: str - Name of the glue data catalog database where schemas will be written
                    table_prefix: str - Prefix to include on table schema names when written in glue catalog
                    source_db_path: str - Path within source database from which assets will be crawled
        
        env: Environment
            Environment object with region and account details
        """
         
        super().__init__(scope, construct_id, account_props, connection_props, env, **kwargs)
        account_id = account_props['account_id']

        datazone_project_id = connection_props['datazone_project_id']
        glue_connection_props = connection_props['glue_connection']
        glue_crawlers_props = connection_props['glue_crawlers'] if 'glue_crawlers' in connection_props else None
        
        a_common_glue_role_name = GLOBAL_VARIABLES['account']['a_common_glue_role_name']
        a_common_glue_role_arn = f'arn:aws:iam::{account_id}:role/{a_common_glue_role_name}'
        
        glue_crawlers = []
        if glue_crawlers_props:     
            for glue_crawler_id, glue_crawler_props in glue_crawlers_props.items():
                
                glue_crawler = glue.CfnCrawler(
                    scope= self, 
                    id= glue_crawler_id,
                    name= glue_crawler_props["name"],
                    role= a_common_glue_role_arn,
                    database_name= glue_crawler_props["catalog_database_name"],
                    table_prefix= glue_crawler_props["table_prefix"],
                    targets= glue.CfnCrawler.TargetsProperty(
                        jdbc_targets= [
                            glue.CfnCrawler.JdbcTargetProperty(
                                connection_name= glue_connection_props['name'],
                                path=glue_crawler_props["source_db_path"]
                            )
                        ]
                    ),
                    tags= {
                        'datazone:projectId': datazone_project_id
                    }
                )

                glue_crawler.node.add_dependency(self.glue_connection)
                glue_crawlers.append(glue_crawler)