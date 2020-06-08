import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ParamValidationError

from flask_talisman import Talisman

from logger import LOG

CONFIG = {}


def setup_talisman(app):
    csp = {"default-src": ["'self'", "https://*.s3.amazonaws.com"]}
    is_https = get("app_environment", "testing") != "testing"
    log_message = (
        "loading Talisman with HTTPS"
        if is_https
        else "loading Talisman for testing - no HTTPS"
    )
    app.logger.info(log_message)
    return Talisman(
        app,
        force_https=is_https,
        strict_transport_security=is_https,
        session_cookie_secure=is_https,
        content_security_policy=csp,
    )


def load_environment(app):
    """
    Load environment vars into flask app attributes
    """
    global CONFIG
    CONFIG = app.config
    read_env_variables(app)
    set_app_settings(app)


def read_env_variables(app):
    app.secret_key = os.getenv("APPSECRET", "secret")
    set("page_title", os.getenv("PAGE_TITLE", "Data Transfer"))
    set("app_environment", os.getenv("APP_ENVIRONMENT", "testing"))
    set("admin", os.getenv("ADMIN", "false"))
    set("client_id", os.getenv("CLIENT_ID", None))
    set("cognito_domain", os.getenv("COGNITO_DOMAIN", None))
    set("client_secret", os.getenv("CLIENT_SECRET", None))
    set("redirect_host", os.getenv("REDIRECT_HOST"))
    set("bucket_name", os.getenv("BUCKET_NAME"))
    set("bucket_main_prefix", os.getenv("BUCKET_MAIN_PREFIX", "web-app-prod-data"))
    set("bucket_upload_prefix", os.getenv("BUCKET_UPLOAD_PREFIX", "web-app-upload"))
    set("region", os.getenv("REGION", "eu-west-2"))

    # temporary references to existing env vars
    set("cf_space", get("app_environment"))
    set(
        "flask_env", "production" if get("app_environment" == "prod") else "development"
    )
    os.environ["FLASK_ENV"] = get("flask_env")


def set_app_settings(app):
    """
    Use existing env vars if loaded
    """
    if None in [
        get("client_id"),
        get("cognito_domain"),
        get("client_secret"),
    ]:
        cognito_credentials = load_cognito_settings()
        set("cognito_domain", cognito_credentials["cognito_domain"])
        set("client_id", cognito_credentials["client_id"])
        set("client_secret", cognito_credentials["client_secret"])


def setup_local_environment(
    host="localhost", port=8000, is_admin=False, environment=None
):
    region = "eu-west-2"

    os.environ["ADMIN"] = "true" if is_admin else "false"
    # TODO remove once admin app running online
    os.environ["ADMIN_AWS_AUTH"] = "true" if is_admin else "false"

    if environment:
        os.environ["APP_ENVIRONMENT"] = environment
        if environment == "testing":
            os.environ["BUCKET_NAME"] = "backend-consumer-service-test"

    os.environ["PAGE_TITLE"] = "LOCAL COVID-19 Data Transfer"
    os.environ["FLASK_ENV"] = "development"
    os.environ["REDIRECT_HOST"] = f"http://{host}:{port}"
    os.environ["AWS_DEFAULT_REGION"] = region
    os.environ["REGION"] = region


def load_ssm_parameters(app):
    ssm_parameters_retrieved = True
    ssm_prefix = "/transfer-coronavirus-data-service"
    ssm_parameter_map = {
        "/cognito/client_id": "client_id",
        "/cognito/client_secret": "client_secret",  # pragma: allowlist secret
        "/cognito/domain": "cognito_domain",
        "/s3/bucket_name": "bucket_name",
        "/flask/secret_key": "secret_key",
    }

    ssm_client = boto3.client("ssm")

    try:
        ssm_parameters = ssm_client.get_parameters_by_path(
            Path=ssm_prefix, Recursive=True, WithDecryption=True
        )

        for param in ssm_parameters["Parameters"]:
            for param_name, config_var_name in ssm_parameter_map.items():
                if param["Name"].endswith(param_name):

                    # The flask secret_key is attached directly to app
                    # instead of set in app.config
                    if config_var_name == "secret_key":
                        LOG.debug("Set app property: %s from ssm", config_var_name)
                        app.secret_key = param["Value"]

                    set(config_var_name, param["Value"])
                    LOG.debug("Set config var: %s from ssm", config_var_name)

    except ClientError as error:
        LOG.error(error)
        ssm_parameters_retrieved = False
    except NoCredentialsError as error:
        LOG.debug(error)
        ssm_parameters_retrieved = False

    return ssm_parameters_retrieved


def load_cognito_settings():
    client = boto3.client("cognito-idp", region_name="eu-west-2")
    pool_id = env_pool_id()

    client_id = ""
    client_secret = ""
    cognito_domain = ""
    estimated_num_users = 0

    pool_client_resp = client.list_user_pool_clients(UserPoolId=pool_id, MaxResults=2)

    if "UserPoolClients" in pool_client_resp:
        client_id = pool_client_resp["UserPoolClients"][0]["ClientId"]

    if client_id != "":
        desc_client_resp = client.describe_user_pool_client(
            UserPoolId=pool_id, ClientId=client_id
        )
        if "UserPoolClient" in desc_client_resp:
            client_secret = desc_client_resp["UserPoolClient"]["ClientSecret"]

    desc_pool = client.describe_user_pool(UserPoolId=pool_id)
    if "UserPool" in desc_pool:
        cognito_domain = desc_pool["UserPool"]["Domain"]
        estimated_num_users = desc_pool["UserPool"]["EstimatedNumberOfUsers"]

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "cognito_domain": "{}.auth.eu-west-2.amazoncognito.com".format(cognito_domain),
        "estimated_num_users": estimated_num_users,
    }


def get_cognito_pool_name():
    environment = get("app_environment", "testing")
    pool_name_prefix = "corona-cognito-pool"
    if environment == "production":
        suffix = "prod"
    elif environment == "testing":
        suffix = "development"
    else:
        suffix = environment

    pool_name = f"{pool_name_prefix}-{suffix}"
    LOG.debug(
        {
            "pool_name": pool_name,
            "pool_name_prefix": pool_name_prefix,
            "suffix": suffix,
            "environment": environment,
        }
    )

    set("cognito_pool_name", pool_name)

    return pool_name


def env_pool_id():
    pool_id = None
    pool_name = get_cognito_pool_name()

    if pool_name is not None:
        for pool in list_pools():
            if pool["name"] == pool_name:
                pool_id = pool["id"]
                break

    LOG.debug({"pool_name": pool_name, "pool_id": pool_id})

    return pool_id


def list_pools():
    client = boto3.client("cognito-idp", region_name="eu-west-2")
    pool_list = []
    try:
        response = client.list_user_pools(MaxResults=10)
    except (ClientError, ParamValidationError) as error:
        LOG.error(error)
        response = {}
    if "UserPools" in response:
        # convert keys to lower case
        pool_list = [
            {key.lower(): value for key, value in pool.items()}
            for pool in response["UserPools"]
        ]
    return pool_list


def get(setting_name, default=None):
    return CONFIG.get(setting_name, default)


def set(setting_name, value=None):
    CONFIG[setting_name] = value


def delete(setting_name):
    del CONFIG[setting_name]
