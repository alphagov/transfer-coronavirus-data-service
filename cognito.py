#!/usr/bin/env python3

import os
import re

import boto3
from botocore.exceptions import ClientError, ParamValidationError

from cognito_groups import get_group_by_name
from logger import LOG


def load_app_settings():
    client = aws_client()
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


def aws_client():
    return boto3.client("cognito-idp", region_name="eu-west-2")


def env_pool_id():
    pool_id = None
    pool_name = None

    environment = os.getenv("CF_SPACE", "testing")

    if environment == "production":
        pool_name = "corona-cognito-pool-prod"
    elif environment == "staging":
        pool_name = "corona-cognito-pool-staging"
    elif environment == "testing":
        pool_name = "corona-cognito-pool-development"

    if pool_name is not None:
        for pool in list_pools():
            if pool["name"] == pool_name:
                pool_id = pool["id"]
                break

    return pool_id


def list_pools():
    client = aws_client()
    res = []
    response = client.list_user_pools(MaxResults=10)
    if "UserPools" in response:
        for pool in response["UserPools"]:
            res.append({"id": pool["Id"], "name": pool["Name"]})
    return res


# TODO remove below once admin app running online
def is_aws_authenticated():
    """
    If the app is being run locally for staging or production
    you can't redirect through cognito to login
    """
    is_aws_auth = os.getenv("ADMIN_AWS_AUTH", "false") == "true"
    is_testing = os.getenv("CF_SPACE", "testing") not in ["staging", "production"]
    return is_aws_auth and not is_testing


# TODO remove below once admin app running online
def delegate_auth_to_aws(session):
    """
    When running the admin interface locally delegate the
    authentication step to get the user credentials and
    role from the assumed IAM role
    """

    client = boto3.client("sts")
    caller = client.get_caller_identity()
    role_arn = caller.get("Arn", "")
    matched = re.search("assumed-role/([^/]+)/", role_arn)
    # role_name should look like `first.last-role_type`
    role_name = matched.group(1)
    role_name_components = role_name.split("-")
    user_name = role_name_components[0]
    role_type = role_name_components[1]

    if role_type in ["admin", "cognito"]:
        user_group = get_group_by_name("admin-full")
        user_email = f"{user_name}@aws"

        session["attributes"] = {
            "custom:is_la": "0",
            "custom:paths": "",
            "email": user_email,
        }
        session["user"] = user_email
        session["email"] = user_email
        session["details"] = "yes"
        session["group"] = user_group


def create_user(name, email_address, phone_number, is_la, custom_paths):
    create_arguments = {
        "UserAttributes": [
            {"Name": "name", "Value": name},
            {"Name": "email", "Value": email_address},
            {"Name": "email_verified", "Value": "true"},
            {"Name": "phone_number", "Value": phone_number},
            {"Name": "phone_number_verified", "Value": "false"},
            {"Name": "custom:is_la", "Value": is_la},
            {"Name": "custom:paths", "Value": custom_paths},
        ],
        "ForceAliasCreation": False,
        "DesiredDeliveryMediums": ["EMAIL"],
    }
    return make_request("admin_create_user", email_address, create_arguments)


def make_request(
    method_name, email_address, additional_arguments={}, return_response=False
):
    client = aws_client()
    additional_arguments["UserPoolId"] = env_pool_id()
    if email_address:
        additional_arguments["Username"] = email_address
    try:
        response = getattr(client, method_name)(**additional_arguments)
    except (ClientError, ParamValidationError) as e:
        LOG.error("ERROR:  %s - %s", email_address, e)
        return {} if return_response else False

    return response if return_response else parse_response(response)


def parse_response(response):
    if "ResponseMetadata" in response:
        if "HTTPStatusCode" in response["ResponseMetadata"]:
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                return True
    return False
