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
import config

CLIENT_EXCEPTIONS = (ClientError, ParamValidationError)


def get_boto3_client():
    return boto3.client("cognito-idp", region_name=config.get("region"))


def create_user(name, email_address, phone_number, is_la, custom_paths):
    client = get_boto3_client()
    try:
        response = client.admin_create_user(
            UserPoolId=config.get("cognito_pool_id"),
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
            UserPoolId=config.get("cognito_pool_id"),
            Username=email,
            UserAttributes=attributes,
        )
    except (ClientError, ParamValidationError) as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def delete_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_delete_user(
            UserPoolId=config.get("cognito_pool_id"), Username=email
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def disable_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_disable_user(
            UserPoolId=config.get("cognito_pool_id"), Username=email
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def enable_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_enable_user(
            UserPoolId=config.get("cognito_pool_id"), Username=email
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def set_user_settings(email):
    client = get_boto3_client()
    try:
        response = client.admin_set_user_settings(
            UserPoolId=config.get("cognito_pool_id"),
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
            UserPoolId=config.get("cognito_pool_id"),
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
            UserPoolId=config.get("cognito_pool_id"),
            Username=email,
            GroupName=group_name,
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def remove_from_group(email, group_name):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_remove_user_from_group(
            UserPoolId=config.get("cognito_pool_id"),
            Username=email,
            GroupName=group_name,
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return check_response_status_code(response)


def get_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_get_user(
            UserPoolId=config.get("cognito_pool_id"), Username=email
        )
    except CLIENT_EXCEPTIONS as error:
        LOG.error(error)
        response = {}
    return response


def list_groups_for_user(email):
    cognito_client = get_boto3_client()
    try:
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=config.get("cognito_pool_id"), Username=email
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
