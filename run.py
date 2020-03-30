import os

import boto3

from logger import LOG
from main import run


def setup_local_environment(host="localhost", port=8000):

    region = "eu-west-2"
    os.environ["PAGE_TITLE"] = "Coronavirus Backend Data Consumers Service"
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
    ssm_parameters = ssm_client.get_parameters_by_path(
        Path=ssm_prefix, Recursive=True, WithDecryption=True
    )
    for param in ssm_parameters["Parameters"]:
        for param_name, env_var_name in ssm_parameter_map.items():
            if param["Name"].endswith(param_name):
                os.environ[env_var_name] = param["Value"]
                LOG.debug("Set env var: %s from ssm", env_var_name)


if __name__ == "__main__":

    default_host = "localhost"
    default_port = "8000"
    setup_local_environment(default_host, default_port)
    run()
