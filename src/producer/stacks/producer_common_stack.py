from config.common.global_vars import GLOBAL_VARIABLES

from os import path;

from aws_cdk import (
    Environment,
    Stack,
    aws_iam as iam,
    aws_sam as sam,
    aws_lambda as lambda_,
    aws_lakeformation as lakeformation,
)

from constructs import Construct

class DataZoneConnectorsProducerCommonStack(Stack):
    """ Class to represents the stack containing all producer-specific common resources in account."""
    
    def __init__(self, scope: Construct, construct_id: str, account_props: dict, producer_props: dict, common_constructs: dict, env: Environment, **kwargs) -> None:
        """ Class Constructor. Will deploy producer-specific common resources in account based on properties specified as parameter.
        
        Parameters
        ----------
        account_props : dict
            dict with common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        producer_props : dict
            dict with producer-specific common properties for account.
            For more details check config/account/a_<ACCOUNT_ID>_config.py documentation and examples.

        common_constructs: dic
            dict with constructs common to the account. Created in and output of account common stack.
        
        env: Environment
            Environment object with region and account details
        """
        
        super().__init__(scope, construct_id, **kwargs)
        account_id, region = account_props['account_id'], account_props['region']

        # ---------------- Lambda Layer ------------------------
        p_aws_sdk_pandas_layer_arn = f'arn:aws:lambda:{region}:336392948345:layer:AWSSDKPandas-Python38:1'
        p_aws_sdk_pandas_layer = lambda_.LayerVersion.from_layer_version_arn(
            scope=self, 
            id='p_aws_sdk_pandas_layer',
            layer_version_arn=p_aws_sdk_pandas_layer_arn
        )

        p_pyodbc_layer = lambda_.LayerVersion(
            scope=self, 
            id='p_pyodbc_layer',
            layer_version_name='dz_conn_p_pyodbc_layer',
            code=lambda_.AssetCode('libs/python38/pyodbc-layer.zip'),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_8]
        )

        p_oracledb_layer = lambda_.LayerVersion(
            scope=self, 
            id='p_oracledb_layer',
            layer_version_name='dz_conn_p_oracledb_layer',
            code=lambda_.AssetCode('libs/python38/oracledb-layer.zip'),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_8]
        )

        # ----------------------- Lake Formation ---------------------------
        p_lf_tag_key = 'dz_conn_p_access'
        p_lf_tag_value = 'True'
        
        p_lf_tag = lakeformation.CfnTag(
            scope= self,
            id= 'p_lf_tag',
            tag_key= p_lf_tag_key,
            tag_values= [p_lf_tag_value]
        )

        p_lf_tag_principals = producer_props['p_lakeformation_tag_principals']

        a_common_glue_role_name = GLOBAL_VARIABLES['account']['a_common_glue_role_name']

        p_lf_tag_principals = producer_props['p_lakeformation_tag_principals']
        p_lf_tag_principals[f'role_{a_common_glue_role_name}'] = {
            'type_name': f'role/{a_common_glue_role_name}',
            'lf_tag_permission': False,
            'lf_tag_objects_permission': True
        }
        
        a_common_lambda_role_name = GLOBAL_VARIABLES['account']['a_common_lambda_role_name']

        p_lf_tag_principals[f'role_{a_common_lambda_role_name}'] = {
            'type_name': f'role/{a_common_lambda_role_name}',
            'lf_tag_permission': True,
            'lf_tag_objects_permission': True
        }

        p_lf_principal_id_prefix = f'arn:aws:iam::{account_id}'
        p_lf_principal_tag_permissions = []
        p_lf_principal_tag_db_permissions = []
        p_lf_principal_tag_table_permissions = []

        p_lf_common_lambda_admin_settings = lakeformation.CfnDataLakeSettings(
            scope= self, 
            id= "p_lf_common_lambda_admin_settings",
            admins=[
                lakeformation.CfnDataLakeSettings.DataLakePrincipalProperty(
                    data_lake_principal_identifier=f'{p_lf_principal_id_prefix}:role/{a_common_lambda_role_name}'
                )
            ]
        )

        for p_lf_tag_principal_id, p_lf_tag_principal in p_lf_tag_principals.items():
            p_lf_principal_type_name = p_lf_tag_principal['type_name']
            p_lf_tag_permission = p_lf_tag_principal['lf_tag_permission']
            p_lf_tag_objects_permission = p_lf_tag_principal['lf_tag_objects_permission']

            if p_lf_tag_permission:
                p_lf_principal_tag_permission = lakeformation.CfnPrincipalPermissions(
                    scope= self,
                    id= f'p_lf_principal_tag_permission_{p_lf_tag_principal_id}',
                    principal= lakeformation.CfnPrincipalPermissions.DataLakePrincipalProperty(
                        data_lake_principal_identifier= f'{p_lf_principal_id_prefix}:{p_lf_principal_type_name}'
                    ),
                    resource=lakeformation.CfnPrincipalPermissions.ResourceProperty(
                        lf_tag=lakeformation.CfnPrincipalPermissions.LFTagKeyResourceProperty(
                            catalog_id= account_id,
                            tag_key= p_lf_tag_key,
                            tag_values= [p_lf_tag_value]
                        )
                    ),
                    permissions= ["DESCRIBE", "ASSOCIATE"],
                    permissions_with_grant_option= ["DESCRIBE", "ASSOCIATE"]
                )
                
                p_lf_principal_tag_permission.node.add_dependency(p_lf_tag)
                p_lf_principal_tag_permissions.append(p_lf_principal_tag_permission)
            
            if p_lf_tag_objects_permission:
                p_lf_principal_tag_db_permission = lakeformation.CfnPrincipalPermissions(
                    scope= self,
                    id= f'p_lf_principal_tag_db_permission_{p_lf_tag_principal_id}',
                    principal= lakeformation.CfnPrincipalPermissions.DataLakePrincipalProperty(
                        data_lake_principal_identifier= f'{p_lf_principal_id_prefix}:{p_lf_principal_type_name}'
                    ),
                    resource=lakeformation.CfnPrincipalPermissions.ResourceProperty(
                        lf_tag_policy=lakeformation.CfnPrincipalPermissions.LFTagPolicyResourceProperty(
                            catalog_id= account_id,
                            expression=[lakeformation.CfnPrincipalPermissions.LFTagProperty(
                                tag_key= p_lf_tag_key,
                                tag_values= [p_lf_tag_value]
                            )],
                            resource_type= 'DATABASE'
                        )
                    ),
                    permissions= ["ALL"],
                    permissions_with_grant_option= ["ALL"]
                )

                p_lf_principal_tag_db_permission.node.add_dependency(p_lf_tag)
                p_lf_principal_tag_db_permissions.append(p_lf_principal_tag_db_permission)

                p_lf_principal_tag_table_permission = lakeformation.CfnPrincipalPermissions(
                    scope= self,
                    id= f'lf-principal-tag-table-permission-{p_lf_tag_principal_id}',
                    principal= lakeformation.CfnPrincipalPermissions.DataLakePrincipalProperty(
                        data_lake_principal_identifier= f'{p_lf_principal_id_prefix}:{p_lf_principal_type_name}'
                    ),
                    resource=lakeformation.CfnPrincipalPermissions.ResourceProperty(
                        lf_tag_policy=lakeformation.CfnPrincipalPermissions.LFTagPolicyResourceProperty(
                            catalog_id= account_id,
                            expression=[lakeformation.CfnPrincipalPermissions.LFTagProperty(
                                tag_key= p_lf_tag_key,
                                tag_values= [p_lf_tag_value]
                            )],
                            resource_type= 'TABLE'
                        )
                    ),
                    permissions= ["ALL"],
                    permissions_with_grant_option= ["ALL"]
                )

                p_lf_principal_tag_table_permission.node.add_dependency(p_lf_tag)
                p_lf_principal_tag_table_permissions.append(p_lf_principal_tag_table_permission)

        # ---------------- Lambda ------------------------        
        p_add_lf_tag_environment_dbs_lambda = lambda_.Function(
            scope= self,
            id= 'p_add_lf_tag_environment_dbs_lambda',
            function_name= GLOBAL_VARIABLES['producer']['p_add_lf_tag_environment_dbs_lambda_name'],
            runtime= lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset(path.join('src/producer/code/lambda', "add_lf_tag_environment_dbs")),
            handler= "add_lf_tag_environment_dbs.handler",
            role= common_constructs['a_common_lambda_role'],
            environment= {
                'P_LAKEFORMATION_TAG_KEY': p_lf_tag_key,
                'P_LAKEFORMATION_TAG_VALUE': p_lf_tag_value
            }
        )
        
        # -------------- Outputs --------------------
        self.outputs = {
            'p_aws_sdk_pandas_layer': p_aws_sdk_pandas_layer,
            'p_pyodbc_layer': p_pyodbc_layer,
            'p_oracledb_layer': p_oracledb_layer,
            'p_add_lf_tag_environment_dbs_lambda': p_add_lf_tag_environment_dbs_lambda
        }




