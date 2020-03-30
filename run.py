import os
import sys

import boto3
from botocore.exceptions import ClientError

from logger import LOG
from main import run


def setup_local_environment(host="localhost", port=8000, is_admin=False, environment=None):

    region = "eu-west-2"

    os.environ["ADMIN"] = "true" if is_admin else "false"

    if environment:
        title = "COVID-19 Data Transfer"
        if environment != "production":
            title = f"{environment.upper()} - {title}"
            os.environ["BUCKET_NAME"] = "backend-consumer-service-test"

        os.environ["PAGE_TITLE"] = title
        os.environ["FLASK_ENV"] = "development"
        os.environ["CF_SPACE"] = environment

    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["REDIRECT_HOST"] = f"http://{host}:{port}"
    os.environ["AWS_DEFAULT_REGION"] = region
    os.environ["REGION"] = region

    ssm_prefix = "/transfer-coronavirus-data-service"
    ssm_parameter_map = {
        "/cognito/client_id": "CLIENT_ID",
        "/cognito/client_secret": "CLIENT_SECRET",
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


if __name__ == "__main__":

    if len(sys.argv) > 2:
        is_admin = sys.argv[1] == "admin"
        admin_env = sys.argv[2]
    else:
        is_admin = False
        admin_env = None

    setup_local_environment(
        is_admin=is_admin,
        environment=admin_env
    )
    run()
