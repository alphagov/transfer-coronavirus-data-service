import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ParamValidationError

from flask_talisman import Talisman

from logger import LOG


def setup_talisman(app):
    csp = {"default-src": ["'self'", "https://*.s3.amazonaws.com"]}
    is_https = app.app_environment != "testing"
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
    app.secret_key = os.getenv("APPSECRET", "secret")
    app.config["client_id"] = os.getenv("CLIENT_ID", None)
    app.config["cognito_domain"] = os.getenv("COGNITO_DOMAIN", None)
    app.config["client_secret"] = os.getenv("CLIENT_SECRET", None)
    app.config["redirect_host"] = os.getenv("REDIRECT_HOST")
    app.config["bucket_name"] = os.getenv("BUCKET_NAME")
    app.config["region"] = os.getenv("REGION")
    set_app_settings(app)


def set_app_settings(app):
    """
    Use existing env vars if loaded
    """
    if None in [
        app.config["client_id"],
        app.config["cognito_domain"],
        app.config["client_secret"],
    ]:
        cognito_credentials = load_cognito_settings()
        app.config["cognito_domain"] = cognito_credentials["cognito_domain"]
        app.config["client_id"] = cognito_credentials["client_id"]
        app.config["client_secret"] = cognito_credentials["client_secret"]


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
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["REDIRECT_HOST"] = f"http://{host}:{port}"
    os.environ["AWS_DEFAULT_REGION"] = region
    os.environ["REGION"] = region

    ssm_prefix = "/transfer-coronavirus-data-service"
    ssm_parameter_map = {
        "/cognito/client_id": "CLIENT_ID",
        "/cognito/client_secret": "CLIENT_SECRET",  # pragma: allowlist secret
        "/cognito/domain": "COGNITO_DOMAIN",
        "/s3/bucket_name": "BUCKET_NAME",
    }

    ssm_client = boto3.client("ssm")

    try:
        ssm_parameters = ssm_client.get_parameters_by_path(
            Path=ssm_prefix, Recursive=True, WithDecryption=True
        )

        for param in ssm_parameters["Parameters"]:
            for param_name, env_var_name in ssm_parameter_map.items():
                if param["Name"].endswith(param_name):
                    os.environ[env_var_name] = param["Value"]
                    LOG.debug("Set env var: %s from ssm", env_var_name)

    except ClientError as error:
        LOG.error(error)
    except NoCredentialsError:
        green_char = "\033[92m"
        end_charac = "\033[0m"
        print("-" * 35)
        print("Please run: {}eval $(gds aws XXXX -e){}".format(green_char, end_charac))
        print("Where {}XXXX{} is the account to access".format(green_char, end_charac))
        print("Then run make again")
        print("-" * 35)
        exit()


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
    environment = os.getenv("APP_ENVIRONMENT", "testing")
    pool_name_prefix = "corona-cognito-pool-"
    if environment == "production":
        pool_name = f"{pool_name_prefix}prod"
    elif environment == "staging":
        pool_name = f"{pool_name_prefix}staging"
    elif environment == "testing":
        pool_name = f"{pool_name_prefix}development"

    return pool_name


def env_pool_id():
    pool_id = None
    pool_name = None

    pool_name = get_cognito_pool_name()

    if pool_name is not None:
        for pool in list_pools():
            if pool["name"] == pool_name:
                pool_id = pool["id"]
                break

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
