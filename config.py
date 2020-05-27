import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask_talisman import Talisman

import cognito
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
        cognito_credentials = cognito.load_app_settings()
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
