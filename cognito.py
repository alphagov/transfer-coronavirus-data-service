#!/usr/bin/env python3
"""
The Cognito IDP API makes a distinction between operations a
user can do on their own account and operations an administrator
can do to any user account.

API operations prefixed with admin_ are operations administrators
perform on behalf of other users.
"""

import os
import re

import boto3
from botocore.exceptions import ClientError, ParamValidationError

from cognito_groups import get_group_by_name, get_group_map
from logger import LOG

CLIENT_EXCEPTIONS = (ClientError, ParamValidationError)


def load_app_settings():
    client = get_boto3_client()
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


def get_boto3_client():
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
    client = get_boto3_client()
    pool_list = []
    try:
        response = client.list_user_pools(MaxResults=10)
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    if "UserPools" in response:
        # convert keys to lower case
        pool_list = [
            {key.lower(): value for key, value in pool.items()}
            for pool in response["UserPools"]
        ]
    return pool_list


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
    client = get_boto3_client()
    try:
        response = client.admin_create_user(
            UserPoolId=env_pool_id(),
            Username=email_address,
            UserAttributes=[
                {"Name": "name", "Value": name},
                {"Name": "email", "Value": email_address},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "phone_number", "Value": phone_number},
                {"Name": "phone_number_verified", "Value": "false"},
                {"Name": "custom:is_la", "Value": is_la},
                {"Name": "custom:paths", "Value": custom_paths},
            ],
            ForceAliasCreation=False,
            DesiredDeliveryMediums=["EMAIL"],
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return "User" in response


def update_user(email, attributes):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_update_user_attributes(
            UserPoolId=env_pool_id(), Username=email, UserAttributes=attributes
        )
    except (ClientError, ParamValidationError) as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def delete_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_delete_user(
            UserPoolId=env_pool_id(), Username=email
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def disable_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_disable_user(
            UserPoolId=env_pool_id(), Username=email
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def enable_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_enable_user(
            UserPoolId=env_pool_id(), Username=email
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def set_user_settings(email):
    client = get_boto3_client()
    try:
        response = client.admin_set_user_settings(
            UserPoolId=env_pool_id(),
            Username=email,
            MFAOptions=[{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def set_mfa_preferences(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_set_user_mfa_preference(
            UserPoolId=env_pool_id(),
            Username=email,
            SMSMfaSettings={"Enabled": True, "PreferredMfa": True},
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def add_to_group(email, group_name):
    if group_name is None:
        group_name = "standard-download"
    if group_name not in get_group_map().keys():
        return False

    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_add_user_to_group(
            UserPoolId=env_pool_id(), Username=email, GroupName=group_name
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def remove_from_group(email, group_name):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_remove_user_from_group(
            UserPoolId=env_pool_id(), Username=email, GroupName=group_name
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def get_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_get_user(
            UserPoolId=env_pool_id(), Username=email
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return response


def list_groups_for_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=env_pool_id(), Username=email
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return response


def check_response_status_code(response):
    is_200 = False
    if "ResponseMetadata" in response:
        if "HTTPStatusCode" in response["ResponseMetadata"]:
            is_200 = response["ResponseMetadata"]["HTTPStatusCode"] == 200

    return is_200
