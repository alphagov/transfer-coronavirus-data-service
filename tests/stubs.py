""" Create mock boto3 clients for testing """

import boto3
import pytest
from botocore.stub import Stubber


def _keep_it_real():
    """ Keep the native """
    if not getattr(boto3, "real_client", None):
        boto3.real_client = boto3.client


def mock_s3_list_objects(bucket_name, prefixes):
    _keep_it_real()
    client = boto3.real_client("s3")

    stubber = Stubber(client)

    for prefix in prefixes:
        mock_list_objects_1 = {
            "Contents": [
                {"Key": f"{prefix}/people1.csv", "Size": 100},
                {"Key": f"{prefix}/people2.csv", "Size": 200},
                {"Key": f"{prefix}/nested/nested_people1.csv", "Size": 300},
            ],
            "IsTruncated": True,
            "NextMarker": "page-2",
        }

        stubber.add_response(
            "list_objects",
            mock_list_objects_1,
            {"Bucket": bucket_name, "Prefix": prefix},
        )

        mock_list_objects_2 = {
            "Contents": [
                {"Key": f"{prefix}/people3.csv", "Size": 100},
                {"Key": f"{prefix}/people4.csv", "Size": 200},
            ]
        }

        stubber.add_response(
            "list_objects",
            mock_list_objects_2,
            {"Bucket": bucket_name, "Prefix": prefix, "Marker": "page-2"},
        )

    # replace the get_presigned_url so it runs without AWS creds
    client.generate_presigned_url = (
        lambda op, Params, ExpiresIn, HttpMethod: f".co/{Params['Bucket']}/{Params['Key']}"
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name, config=None: client
    return stubber


def mock_cognito_auth_flow(token):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    mock_get_user = {
        "Username": "test-secrets",
        "UserAttributes": [
            {"Name": "custom:paths", "Value": "local_authority/barnet"},
            {"Name": "custom:is_la", "Value": "1"},
        ],
    }

    stubber.add_response("get_user", mock_get_user, {"AccessToken": token})

    mock_list_user_pools = {
        "UserPools": [
            {"Id": "eu-west-2_poolid", "Name": "corona-cognito-pool-development"}
        ]
    }
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    mock_admin_list_groups_for_user = {
        "Groups": [
            {
                "GroupName": "standard-download",
                "UserPoolId": "eu-west-2_poolid",
                "Description": "Standard download user",
            }
        ]
    }
    stubber.add_response(
        "admin_list_groups_for_user",
        mock_admin_list_groups_for_user,
        {"UserPoolId": "eu-west-2_poolid", "Username": "test-secrets", "Limit": 10},
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_create_user(admin_user):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    mock_list_user_pools = {
        "UserPools": [
            {"Id": "eu-west-2_poolid", "Name": "corona-cognito-pool-development"}
        ]
    }
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    mock_create_user = {
        "User": {
            "Username": admin_user["email"],
            "Attributes": [
                {"Name": "name", "Value": admin_user["name"]},
                {"Name": "email", "Value": admin_user["email"]},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "phone_number", "Value": admin_user["phone_number"]},
                {"Name": "phone_number_verified", "Value": "false"},
                {"Name": "custom:is_la", "Value": admin_user["custom:is_la"]},
                {"Name": "custom:paths", "Value": admin_user["custom:paths"]},
            ],
            "Enabled": True
        }
    }
    params_create_user = {
        "UserPoolId": "eu-west-2_poolid",
        "Username": admin_user["email"],
        "UserAttributes": [
            {"Name": "name", "Value": admin_user["name"]},
            {"Name": "email", "Value": admin_user["email"]},
            {"Name": "email_verified", "Value": "true"},
            {"Name": "phone_number", "Value": admin_user["phone_number"]},
            {"Name": "phone_number_verified", "Value": "false"},
            {"Name": "custom:is_la", "Value": admin_user["custom:is_la"]},
            {"Name": "custom:paths", "Value": admin_user["custom:paths"]},
        ],
        "ForceAliasCreation": False,
        "DesiredDeliveryMediums": ["EMAIL"],
    }

    stubber.add_response("admin_create_user", mock_create_user, params_create_user)

    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    # TODO: stub boto3 calls in cognito 443 & 451

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber
