# ------------------ Account ------------------------
"""
ACCOUNT_PROPS dict will be used to consolidate common properties for an account with producer / consumer capabilities.
The dict structures includes:
    account_id: str - Account id
    region: str - Region
    service_portfolio: dict - Dict containing properties for account service portfolio including:
        access_role_names: list - Name of the roles that are able to access / manage the service portfolio.
    vpc: dict - Dict containing properties for account vpc including:
        vpc_id: str - Id of the vpc
        availability_zones: list - List of Availability Zones covering the vpc
        private_subnets: list - List of subnet ids of the vpc
        security_groups: list - List of security groups of the vpc
    s3: dict - Dict containing properties for account S3 setup including:
        bucket_name: str - Name of the bucket to be created by solution to store data associated to its use.
"""
ACCOUNT_PROPS = {
    'account_id': '',
    'region': '',
    'service_portfolio': {
        'access_role_names': []
    },
    'vpc': {
        'vpc_id': '',
        'availability_zones': [],
        'private_subnets': [],
        'security_groups': []
    },
    's3': {
        'bucket_name': 'dz-conn-a-<ACCOUNT_ID>-<REGION>'
    }
}

# ------------------ Producer ------------------------ 
"""
PRODUCER_PROPS dict will be used to consolidate common producer-related properties for an account.
The dict structures includes:
    p_lakeformation_tag_principals: dict - Dict containing properties for lake formation tag principals. Each key represents a principal; key (assigned by you) will be used as resource physical id and value is a dict including:
        type_name: str - IAM principal type and name in the format '{PRINCIPAL_TYPE}/{PRINCIPAL_NAME_PATH}'. For example 'role/Admin'.
        lf_tag_permission: bool - If principal should have admin permission on top of the lake formation tag deployed as part of the solution.
        lf_tag_objects_permission: bool - If principal should have admin permission on top of objects tagged with the lake formation tag deployed as part of the solution.
"""
PRODUCER_PROPS = {
    'p_lakeformation_tag_principals': {
        '': {
            'type_name': '',
            'lf_tag_permission': False,
            'lf_tag_objects_permission': False
        }
    }
}

"""
PRODUCER_WORKFLOW_PROPS dict will be used to consolidate producer workflow properties for an account.
The dict structures includes a key (not to be modified) per workflow:
    p_manage_subscription_grant: dict - Dict containing properties for managing subscription grants in the producer side including:
        vpc_id: str - Id of the vpc where lambda function connecting to data sources will be allocated
        vpc_private_subnet_ids: list - List of subnet ids of the vpc where lambda function connecting to data sources will be allocated
        vpc_security_group_ids: list - List of security groups of the vpc that will be associated to the lambda function connecting to data sources
    p_manage_subscription_revoke: dict - Dict containing properties for managing subscription revocations in the producer side including:
        vpc_id: str - Id of the vpc where lambda function connecting to data sources will be allocated
        vpc_private_subnet_ids: list - List of subnet ids of the vpc where lambda function connecting to data sources will be allocated
        vpc_security_group_ids: list - List of security groups of the vpc that will be associated to the lambda function connecting to data sources
        secret_recovery_window_in_days: str - Number of days (min '7') to use as retention window when scheduling deletion of secrets
"""
PRODUCER_WORKFLOW_PROPS = {
    'p_manage_subscription_grant': {
        'vpc_id': ACCOUNT_PROPS['vpc']['vpc_id'],
        'vpc_private_subnet_ids': ACCOUNT_PROPS['vpc']['private_subnets'],
        'vpc_security_group_ids': ACCOUNT_PROPS['vpc']['security_groups']
    },
    'p_manage_subscription_revoke': {
        'vpc_id': ACCOUNT_PROPS['vpc']['vpc_id'],
        'vpc_private_subnet_ids': ACCOUNT_PROPS['vpc']['private_subnets'],
        'vpc_security_group_ids': ACCOUNT_PROPS['vpc']['security_groups'],
        'secret_recovery_window_in_days': '7'
    }
}

"""
PRODUCER_SERVICE_PORTFOLIO_PROPS dict will be used to consolidate producer service portfolio product properties for an account.
The dict structures includes:
    p_product_default_props: dict - Dict containing default values for producer products in the service catalog portfolio of the account. Each key (not to be modified) represents a product:
        glue_jdbc_connector: dict - Dict containing default values for Glue JDBC Connector product including:
            ssl: bool - Default value for enforcing ssl on glue connection when deployed.
            availability_zone: str - Default value for the availability zone where glue connection will be deployed.
            security_group_ids: list - Default value for list of security groups to be assigned to glue connection when deployed.
            subnet_id: str - Default value for the subnet where glue connection will be deployed.
        glue_jdbc_connector_with_crawler: dict - Dict containing default values for Glue JDBC Connector with Crawler product
            ssl: bool - Default value for enforcing ssl on glue connection when deployed.
            availability_zone: str - Default value for the availability zone where glue connection will be deployed.
            security_group_ids: list - Default value for list of security groups to be assigned to glue connection when deployed.
            subnet_id: str - Default value for the subnet where glue connection will be deployed.
"""
PRODUCER_SERVICE_PORTFOLIO_PROPS = {
    'p_product_default_props': {
        'glue_jdbc_connector': {
            'ssl': True,
            'availability_zone': ACCOUNT_PROPS['vpc']['availability_zones'][0],
            'security_group_ids': ACCOUNT_PROPS['vpc']['security_groups'],
            'subnet_id': ACCOUNT_PROPS['vpc']['private_subnets'][0]
        },
        'glue_jdbc_connector_with_crawler': {
            'ssl': True,
            'availability_zone': ACCOUNT_PROPS['vpc']['availability_zones'][0],
            'security_group_ids': ACCOUNT_PROPS['vpc']['security_groups'],
            'subnet_id': ACCOUNT_PROPS['vpc']['private_subnets'][0]
        }
    }
}

# ------------------ Consumer ------------------------
"""
CONSUMER_WORKFLOW_PROPS dict will be used to consolidate consumer workflow properties for an account.
The dict structures includes a key (not to be modified) per workflow:
    c_manage_subscription_grant: dict - Dict containing properties for managing subscription grants in the consumer side. Reserved for future use (Leave as empty dict).
    c_manage_subscription_revoke: dict - Dict containing properties for managing subscriptions revocations in the consumer side including:
        secret_recovery_window_in_days: str - Number of days (min '7') to use as retention window when scheduling deletion of secrets
"""
CONSUMER_WORKFLOW_PROPS = {
    'c_manage_subscription_grant': { },
    'c_manage_subscription_revoke': { 
        'secret_recovery_window_in_days': '7'
    }
}

"""
CONSUMER_SERVICE_PORTFOLIO_PROPS dict will be used to consolidate consumer service portfolio product properties for an account.
The dict structures includes:
    c_product_default_props: dict - Dict containing default values for consumer products in the service catalog portfolio of the account. Each key (not to be modified) represents a product:
        athena_mysql_jdbc_connector: dict - Dict containing default values for Athena MySQL JDBC Connection product including:
            port: str - Default value for port to be used when connecting to source database.
            security_group_ids: list - Default value for list of security groups to be assigned to athena connection's underlying lambda when deployed.
            subnet_ids: list - Default value for the list of subnets where athena connection's underlying lambda will be deployed.
        athena_postgres_jdbc_connector: dict - Dict containing default values for Athena PostgreSQL JDBC Connection product
            port: str - Default value for port to be used when connecting to source database.
            security_group_ids: list - Default value for list of security groups to be assigned to athena connection's underlying lambda when deployed.
            subnet_ids: list - Default value for the list of subnets where athena connection's underlying lambda will be deployed.
        athena_sqlserver_jdbc_connector: dict - Dict containing default values for Athena SQL Server JDBC Connection product
            port: str - Default value for port to be used when connecting to source database.
            security_group_ids: list - Default value for list of security groups to be assigned to athena connection's underlying lambda when deployed.
            subnet_ids: list - Default value for the list of subnets where athena connection's underlying lambda will be deployed.
            ssl: str - 'true' or 'false' depending if ssl should be used when connecting to source database
        athena_oracle_jdbc_connector: dict - Dict containing default values for Athena Oracle JDBC Connection product
            port: str - Default value for port to be used when connecting to source database.
            security_group_ids: list - Default value for list of security groups to be assigned to athena connection's underlying lambda when deployed.
            subnet_ids: list - Default value for the list of subnets where athena connection's underlying lambda will be deployed.
"""
CONSUMER_SERVICE_PORTFOLIO_PROPS = {
    'c_product_default_props': {
        'athena_mysql_jdbc_connector': {
            'port': '3306',
            'security_group_ids': ACCOUNT_PROPS['vpc']['security_groups'],
            'subnet_ids': ACCOUNT_PROPS['vpc']['private_subnets']
        },
        'athena_postgres_jdbc_connector': {
            'port': '5432',
            'security_group_ids': ACCOUNT_PROPS['vpc']['security_groups'],
            'subnet_ids': ACCOUNT_PROPS['vpc']['private_subnets']
        },
        'athena_sqlserver_jdbc_connector': {
            'port': '1433',
            'security_group_ids': ACCOUNT_PROPS['vpc']['security_groups'],
            'subnet_ids': ACCOUNT_PROPS['vpc']['private_subnets'],
            'ssl': 'true'
        },
        'athena_oracle_jdbc_connector': {
            'port': '1521',
            'security_group_ids': ACCOUNT_PROPS['vpc']['security_groups'],
            'subnet_ids': ACCOUNT_PROPS['vpc']['private_subnets']
        }
    }
}