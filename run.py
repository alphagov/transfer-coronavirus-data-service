import os
import sys

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from logger import LOG
from main import run


def setup_local_environment(
    host="localhost", port=8000, is_admin=False, environment=None
):

    region = "eu-west-2"

    os.environ["ADMIN"] = "true" if is_admin else "false"

    if environment:
        os.environ["CF_SPACE"] = environment
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
    except NoCredentialsError:
        green_char = "\033[92m"
        end_charac = "\033[0m"
        print("-" * 35)
        print("Please run: {}eval $(gds aws XXXX -e){}".format(green_char, end_charac))
        print("Where {}XXXX{} is the account to access".format(green_char, end_charac))
        print("Then run make again")
        print("-" * 35)
        exit()


if __name__ == "__main__":

    if len(sys.argv) == 3:
        is_admin = sys.argv[1] == "admin"
        env_load = sys.argv[2]
    else:
        is_admin = False
        env_load = "testing"

    green_char = "\033[92m"
    end_charac = "\033[0m"

    print("-" * 35)
    print(
        "Running {0}{2}{1} for: {0}{3}{1}".format(
            green_char,
            end_charac,
            "admin tool" if is_admin else "download tool frontend",
            env_load,
        )
    )

    if sys.argv[0] == "run.py":
        cont = "y"
        if env_load != "testing":
            try:
                cont = input("Not {}testing{}; do you want to continue? (Y/n) ".format(green_char, end_charac)).lower()
                if cont == "":
                    cont = "y"
            except KeyboardInterrupt:
                print("\nRegistration cancelled.")
                exit()
        if cont != "y":
            exit()
    print("-" * 35)

    setup_local_environment(is_admin=is_admin, environment=env_load)
    run()
