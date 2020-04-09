#!/usr/bin/env python3

# import json

# import csv
import os
import re
import time

import boto3
from botocore.exceptions import ClientError
from flask import session

from cognito_groups import get_group_by_name, get_group_map, user_groups
from logger import LOG

# from validate_email import validate_email


class CognitoException(Exception):
    def __init__(self, type, msg=None):
        self.type = type
        self.msg = msg  # you could add more args

    def __str__(self):
        return "{}: {}".format(self.type, self.msg if self.msg is not None else "")


def get_boto3_client():
    client = boto3.client("cognito-idp", region_name="eu-west-2")
    return client


def load_app_settings():
    client = get_boto3_client()
    pool_id = get_env_pool_id()

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


def allowed_domains():
    return [
        ".gov.uk",  # allow any *.gov.uk email
        "@brake.co.uk",  # allow @brake.co.uk (wholesaler)
        "@nhs.net",
        "@tesco.com",
        "@ocadoretail.com",
        "@morrisonsplc.co.uk",
        "@sainsburys.co.uk",
        "@iceland.co.uk",
        "@coop.co.uk",
        "@asda.co.uk",
        "@johnlewis.co.uk",
    ]


def return_false_if_unexpected_domain(email_address):
    res = False

    # ALLOWS
    for domain in allowed_domains():
        if email_address.endswith(domain):
            res = True

    # DENIES - these override ALLOWS
    # the reason is these people support the system
    # but shouldn't have access
    for domain in [
        # "@digital.cabinet-office.gov.uk",
        # "@cabinet-office.gov.uk",
        # "@localdigital.gov.uk",
        # "@communities.gov.uk",
    ]:
        if email_address.endswith(domain):
            res = False

    return res


def get_env_pool_id():
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
    res = []
    response = client.list_user_pools(MaxResults=10)
    if "UserPools" in response:
        for pool in response["UserPools"]:
            res.append({"id": pool["Id"], "name": pool["Name"]})
    return res


def sanitise_email(email_address):
    if "@" in email_address:
        email_address = email_address.strip().lower().encode("latin1").decode("utf-8")
        if return_false_if_unexpected_domain(email_address):
            return email_address
        else:
            raise CognitoException(
                type="BadEmailWhitelist", msg="failed for '{}'".format(email_address)
            )
    raise CognitoException(type="BadEmail")


def sanitise_phone(phone_number):
    if phone_number != "":
        phone_number = re.sub(r"[^0-9]", "", phone_number)
        if phone_number.startswith("0"):
            phone_number = "+44" + phone_number[1:]
        if phone_number.startswith("44"):
            phone_number = "+44" + phone_number[2:]
        return phone_number
    return ""


def sanitise_name(name):
    if name != "":
        name = re.sub(r"[^a-zA-Z0-9-_\']", "", name)
        return name
    return ""


def san_row(row):

    row["email"] = sanitise_email(row["email"])
    if row["email"] == "":
        return {}

    row["phone_number"] = sanitise_phone(row["phone_number"])
    if row["phone_number"] == "":
        return {}

    return row


def get_user_details(email_address):
    client = get_boto3_client()
    try:
        san_email_address = sanitise_email(email_address)
        if san_email_address != "":
            user = client.admin_get_user(
                UserPoolId=get_env_pool_id(), Username=san_email_address
            )
            return normalise_user(user)
    except ClientError as error:
        LOG.debug({"error":error})
    return {}


def users_group(username):
    groups = []

    client = get_boto3_client()
    response = client.admin_list_groups_for_user(
        Username=username, UserPoolId=get_env_pool_id(), Limit=10
    )

    if "Groups" in response:
        for group in response["Groups"]:
            if "GroupName" in group:
                groups.append(group["GroupName"])

    LOG.debug(groups)

    # return return_users_group(groups)
    # Currently you can attach a list of users in cognito
    # but we're currently only interested in the first group
    group_name = None if len(groups) == 0 else groups[0]
    return get_group_by_name(group_name)


def normalise_user(aws_user_resp):
    res = {}
    if "Username" in aws_user_resp:
        res = {
            "username": aws_user_resp["Username"],
            "status": aws_user_resp["UserStatus"],
            "createdate": aws_user_resp["UserCreateDate"],
            "lastmodifieddate": aws_user_resp["UserLastModifiedDate"],
            "enabled": aws_user_resp["Enabled"],
        }
        for attr in aws_user_resp[
            "Attributes" if "Attributes" in aws_user_resp else "UserAttributes"
        ]:
            res[attr["Name"]] = attr["Value"]

    if "username" in res:
        res["group"] = users_group(res["username"])

    return res


def list_users(email_starts_filter="", token="", limit=20):
    client = get_boto3_client()
    arguments = {
        "UserPoolId": get_env_pool_id(),
        "AttributesToGet": [
            "name",
            "email",
            "email_verified",
            "phone_number",
            "phone_number_verified",
            "cognito:user_status",
            "custom:paths",
            "custom:is_la",
        ],
        "Limit": limit,
    }

    if email_starts_filter != "":
        arguments["Filter"] = 'email ^= "{}"'.format(email_starts_filter)
    if token != "":
        arguments["PaginationToken"] = token

    response = client.list_users(**arguments)

    # LOG.debug({ "action": "list-users", "response": response })

    token = ""
    users = []

    if "Users" in response:
        for user in response["Users"]:
            user_to_add = normalise_user(user)
            if user_to_add != {}:
                users.append(user_to_add)

        if "PaginationToken" in response:
            token = response["PaginationToken"]

        # this is a weird edge case where users could be blank but there is
        # a token for getting more users
        if len(response["Users"]) == 0 and token != "":
            return list_users(
                email_starts_filter=email_starts_filter, limit=limit, token=token
            )

    return {"users": users, "token": token}


def return_false_if_paths_bad(is_la_value, paths_semicolon_seperated):
    if paths_semicolon_seperated == "":
        return False

    app_authorised_paths = [os.getenv("BUCKET_MAIN_PREFIX", "web-app-prod-data")]
    for authed_path in app_authorised_paths:
        for path_re_split_for_check in paths_semicolon_seperated.split(";"):

            # if current/new attr for is_la is 0 (not a local authority)
            # then don't allow local local_authority paths to be set
            if is_la_value == "0":
                if path_re_split_for_check.startswith(
                    "{}/local_authority/".format(authed_path)
                ):
                    LOG.error(
                        "%s: won't set non-LA user to: %s" "user-admin",
                        path_re_split_for_check,
                    )
                    return False
            # if current/new attr for is_la is 1 (IS local authority)
            # then only allow local local_authority paths to be set
            if is_la_value == "1":
                if not path_re_split_for_check.startswith(
                    "{}/local_authority/".format(authed_path)
                ):
                    LOG.debug(
                        "%s: won't set LA user to: %s",
                        "user-admin",
                        path_re_split_for_check,
                    )
                    return False

    return True


def reinvite_user(email_address, confirm=False):
    if confirm:
        user = get_user_details(email_address)
        if user != {}:
            del_res = delete_user(email_address, confirm)
            LOG.debug({"action": "delete-user", "response": del_res})
            if del_res:
                cre_res = create_user(
                    name=user["name"],
                    email_address=user["email"],
                    phone_number=user["phone_number"],
                    attr_paths=user["custom:paths"],
                    is_la=user["custom:is_la"],
                    group_name=user["group"]["value"],
                )
                LOG.debug({"action": "create-user", "response": "cre_res"})
                return cre_res
    return False


def create_and_list_groups():
    groups_res = []
    client = get_boto3_client()

    user_pool_group_names = []
    list_groups_response = client.list_groups(UserPoolId=get_env_pool_id(), Limit=10)
    if "ResponseMetadata" in list_groups_response:
        if "HTTPStatusCode" in list_groups_response["ResponseMetadata"]:
            if list_groups_response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                user_pool_group_names = [
                    group["GroupName"] for group in list_groups_response["Groups"]
                ]

    if len(user_pool_group_names) == 0:
        return groups_res

    for user_group in user_groups():
        if user_group["value"] in user_pool_group_names:
            groups_res.append(user_group)
        else:
            cg_res = client.create_group(
                GroupName=user_group["value"],
                UserPoolId=get_env_pool_id(),
                Description=user_group["display"],
                Precedence=user_group["preference"],
            )
            if "ResponseMetadata" in cg_res:
                if "HTTPStatusCode" in cg_res["ResponseMetadata"]:
                    if cg_res["ResponseMetadata"]["HTTPStatusCode"] == 200:
                        groups_res.append(user_group)

    return groups_res


def add_user_to_group(username, group_name=None):
    client = get_boto3_client()

    if group_name is None:
        group_name = "standard-download"

    group_map = get_group_map()

    if group_name in group_map.keys():
        response = client.admin_add_user_to_group(
            UserPoolId=get_env_pool_id(), Username=username, GroupName=group_name
        )
        if "ResponseMetadata" in response:
            if "HTTPStatusCode" in response["ResponseMetadata"]:
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    session["admin_user_object"]["group"] = group_map[group_name]
                    return True
        else:
            LOG.debug("Failed to add user to group: %s", group_name)
            LOG.debug(response)
    return False


def create_user(
    user
):
    name = user["name"]
    email_address = user["email"]
    phone_number = user["phone_number"]
    attr_paths = user["custom:paths"]
    is_la = user["custom:is_la"]
    group_name = user["group"]["value"]

    client = get_boto3_client()
    email_address = sanitise_email(email_address)
    if email_address == "":
        return False

    phone_number = sanitise_phone(phone_number)
    if phone_number == "":
        return False

    if not return_false_if_paths_bad(is_la, attr_paths):
        return False

    response = []

    try:
        response = client.admin_create_user(
            UserPoolId=get_env_pool_id(),
            Username=email_address,
            UserAttributes=[
                {"Name": "name", "Value": name},
                {"Name": "email", "Value": email_address},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "phone_number", "Value": phone_number},
                {"Name": "phone_number_verified", "Value": "false"},
                {"Name": "custom:is_la", "Value": is_la},
                {"Name": "custom:paths", "Value": attr_paths},
            ],
            ForceAliasCreation=False,
            DesiredDeliveryMediums=["EMAIL"],
        )
    except ClientError as e:
        LOG.error("ERROR:  %s - %s", email_address, e.response["Error"]["Code"])
        return False

    res = False

    if "User" in response:
        if "Enabled" in response["User"]:
            res = response["User"]["Enabled"]

    if res:
        time.sleep(0.1)

        client.admin_set_user_mfa_preference(
            SMSMfaSettings={"Enabled": True, "PreferredMfa": True},
            Username=email_address,
            UserPoolId=get_env_pool_id(),
        )

        time.sleep(0.1)

        client.admin_set_user_settings(
            Username=email_address,
            UserPoolId=get_env_pool_id(),
            MFAOptions=[{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
        )

        time.sleep(0.1)

        add_user_to_group(email_address, group_name)

    return res


def disable_user(email_address, confirm=False):
    client = get_boto3_client()
    if confirm:
        if sanitise_email(email_address) == "":
            LOG.error("ERR: %s: the email %s is not valid", "user-admin", email_address)
            return False

        response = client.admin_disable_user(
            UserPoolId=get_env_pool_id(), Username=email_address
        )
        if "ResponseMetadata" in response:
            if "HTTPStatusCode" in response["ResponseMetadata"]:
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    return True
    return False


def enable_user(email_address, confirm=False):
    client = get_boto3_client()
    if confirm:
        if sanitise_email(email_address) == "":
            LOG.error("ERR: %s: the email %s is not valid", "user-admin", email_address)
            return False

        response = client.admin_enable_user(
            UserPoolId=get_env_pool_id(), Username=email_address
        )
        if "ResponseMetadata" in response:
            if "HTTPStatusCode" in response["ResponseMetadata"]:
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    return True
    return False


def delete_user(email_address, confirm=False):
    client = get_boto3_client()
    if confirm:
        if sanitise_email(email_address) == "":
            LOG.error("ERR: %s: the email %s is not valid", "user-admin", email_address)
            return False

        response = client.admin_delete_user(
            UserPoolId=get_env_pool_id(), Username=email_address
        )
        if "ResponseMetadata" in response:
            if "HTTPStatusCode" in response["ResponseMetadata"]:
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    return True
    return False


def update_user_attributes(user):

    email_address = user["email"]
    new_name = user["name"]
    new_phone_number = user["phone_number"]
    new_paths = user["custom:paths"]
    new_is_la = user["custom:is_la"]
    new_group_name = None if "group" not in user else user["group"]["value"]

    client = get_boto3_client()
    if (
        new_name is None
        and new_phone_number is None
        and new_is_la is None
        and new_paths is None
    ):
        # TODO: will eventually be app.logger.error
        # and SCRIPT will be session["user"]
        LOG.debug("ERR: %s: %s has no new attributes", "user-admin", email_address)
        return False

    if sanitise_email(email_address) == "":
        # TODO: will eventually be app.logger.error
        # and SCRIPT will be session["user"]
        LOG.debug("ERR: %s: the email %s is not valid", "user-admin", email_address)
        return False

    user = get_user_details(email_address)
    if user != {}:
        attrs = []

        # current is_la value
        is_la_value = user["custom:is_la"]

        if new_is_la is not None:
            if isinstance(new_is_la, str):
                # setting is_la value for later checks
                is_la_value = new_is_la
                attrs.append({"Name": "custom:is_la", "Value": new_is_la})
            else:
                LOG.error("ERR: %s: new_is_la is not str", "user-admin")
                return False

        if new_phone_number is not None:
            if isinstance(new_phone_number, str):
                san_phone = sanitise_phone(new_phone_number)
                if san_phone != user["phone_number"]:
                    LOG.debug({"current": user["phone_number"], "new": san_phone})
                    attrs.append({"Name": "phone_number", "Value": san_phone})
                    attrs.append({"Name": "phone_number_verified", "Value": "false"})
            else:
                LOG.error("ERR: %s: phone_number is not str", "user-admin")
                return False

        if new_name is not None:
            if isinstance(new_name, str):
                attrs.append({"Name": "name", "Value": sanitise_name(new_name)})
            else:
                LOG.error("ERR: %s: new_name is not str", "script")
                return False

        if new_paths is not None:
            if isinstance(new_paths, str):

                if not return_false_if_paths_bad(is_la_value, new_paths):
                    return False

                attrs.append({"Name": "custom:paths", "Value": new_paths})
            else:
                LOG.error("ERR: %s: new_paths is not a string", "user-admin")
                return False

        if new_group_name is not None:
            if isinstance(new_group_name, str):
                # current group_name
                old_group_name = user["group"]["value"]

                LOG.debug("Remove user from group: %s", old_group_name)

                rufg_res = client.admin_remove_user_from_group(
                    UserPoolId=get_env_pool_id(),
                    Username=email_address,
                    GroupName=old_group_name,
                )

                if "ResponseMetadata" in rufg_res:
                    if "HTTPStatusCode" in rufg_res["ResponseMetadata"]:
                        if rufg_res["ResponseMetadata"]["HTTPStatusCode"] == 200:
                            LOG.debug("Add user to group: %s", new_group_name)
                            add_user_to_group(email_address, new_group_name)
                else:
                    LOG.debug("Failed to remove user from group: %s", old_group_name)
                    LOG.debug(rufg_res)

            else:
                LOG.error("ERR: %s: new_group_name is not str", "user-admin")
                return False

        if len(attrs) != 0:
            response = client.admin_update_user_attributes(
                UserPoolId=get_env_pool_id(),
                Username=email_address,
                UserAttributes=attrs,
            )
            if "ResponseMetadata" in response:
                if "HTTPStatusCode" in response["ResponseMetadata"]:
                    if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                        return True

    LOG.error("ERR: %s: no actions to take", "user-admin")
    return False
