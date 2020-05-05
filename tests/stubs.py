# """ Create mock boto3 clients for testing """
from datetime import datetime

import boto3
from botocore.stub import Stubber


def _keep_it_real():
    """ Keep the native """
    if not getattr(boto3, "real_client", None):
        boto3.real_client = boto3.client


#
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
    client.generate_presigned_url = lambda op, Params, ExpiresIn, HttpMethod: fake_url(
        Params["Bucket"], Params["Key"]
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name, config=None: client
    return stubber


def mock_cognito_auth_flow(token, test_user):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    mock_get_user = test_user

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
        {"UserPoolId": "eu-west-2_poolid", "Username": "test-secrets"},
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_create_user(admin_user, create_user_arguments):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    user_pool_id = "eu-west-2_poolid"
    group_name = admin_user["group"]["value"]

    mock_list_user_pools = {
        "UserPools": [{"Id": user_pool_id, "Name": "corona-cognito-pool-development"}]
    }
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    mock_admin_create_user = {
        "User": {
            "Username": admin_user["email"],
            "Attributes": create_user_arguments["UserAttributes"],
            "UserCreateDate": datetime.utcnow(),
            "UserLastModifiedDate": datetime.utcnow(),
            "Enabled": True,
            "UserStatus": "FORCE_CHANGE_PASSWORD",
            "MFAOptions": [{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
        },
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    stubber.add_response(
        "admin_create_user", mock_admin_create_user, create_user_arguments
    )
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    mock_admin_set_user_mfa_preference = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    params_admin_set_user_mfa_preference = {
        "SMSMfaSettings": {"Enabled": True, "PreferredMfa": True},
        "Username": admin_user["email"],
        "UserPoolId": user_pool_id,
    }

    stubber.add_response(
        "admin_set_user_mfa_preference",
        mock_admin_set_user_mfa_preference,
        params_admin_set_user_mfa_preference,
    )
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    mock_admin_set_user_settings = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    params_admin_set_user_settings = {
        "UserPoolId": user_pool_id,
        "Username": admin_user["email"],
        "MFAOptions": [{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
    }

    stubber.add_response(
        "admin_set_user_settings",
        mock_admin_set_user_settings,
        params_admin_set_user_settings,
    )
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    mock_admin_add_user_to_group = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    params_admin_add_user_to_group = {
        "Username": admin_user["email"],
        "UserPoolId": user_pool_id,
        "GroupName": group_name,
    }
    stubber.add_response(
        "admin_add_user_to_group",
        mock_admin_add_user_to_group,
        params_admin_add_user_to_group,
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_list_pools(user_pool_id):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    mock_list_user_pools = {
        "UserPools": [{"Id": user_pool_id, "Name": "corona-cognito-pool-development"}]
    }
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_create_user(user_pool_id, user, arguments):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    mock_list_user_pools = {
        "UserPools": [{"Id": user_pool_id, "Name": "corona-cognito-pool-development"}]
    }
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    mock_admin_create_user = {
        "User": {
            "Username": user["email"],
            "Attributes": arguments["UserAttributes"],
            "UserCreateDate": datetime.utcnow(),
            "UserLastModifiedDate": datetime.utcnow(),
            "Enabled": True,
            "UserStatus": "FORCE_CHANGE_PASSWORD",
            "MFAOptions": [{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
        },
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    params_admin_create_user = {
        "UserPoolId": user_pool_id,
        "Username": user["email"],
        **arguments,
    }

    stubber.add_response(
        "admin_create_user", mock_admin_create_user, params_admin_create_user,
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_update_user_attributes(user_pool_id, user, attributes):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    mock_list_user_pools = {
        "UserPools": [{"Id": user_pool_id, "Name": "corona-cognito-pool-development"}]
    }
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})

    mock_admin_update_user_attributes = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    params_admin_update_user_attributes = {
        "UserPoolId": user_pool_id,
        "Username": user["email"],
        "UserAttributes": attributes,
    }

    stubber.add_response(
        "admin_update_user_attributes",
        mock_admin_update_user_attributes,
        params_admin_update_user_attributes,
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_s3_get_object(bucket_name, granted_prefixes, key, success_response):
    _keep_it_real()
    client = boto3.real_client("s3")

    stubber = Stubber(client)

    if any([key.startswith(prefix) for prefix in granted_prefixes]):
        stubber.add_response(
            "get_object", success_response, {"Bucket": bucket_name, "Key": key},
        )
    else:
        stubber.add_client_error(
            "get_object", expected_params={"Bucket": bucket_name, "Key": key}
        )

    # replace the get_presigned_url so it runs without AWS creds
    client.generate_presigned_url = lambda op, Params, ExpiresIn, HttpMethod: fake_url(
        Params["Bucket"], Params["Key"]
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None, config=None: client
    return stubber


def fake_url(bucket, key):
    url = (
        f"https://{bucket}.s3.amazonaws.com/{key}"
        "?X-Amz-Algorithm=AWS4-HMAC-SHA256"
        "&X-Amz-Credential=fake_key%2F20200518%2Feu-west-2%2Fs3%2Faws4_request"
        "&X-Amz-Date=20200518T101632Z"
        "&X-Amz-Expires=60"
        "&X-Amz-SignedHeaders=host"
        "&X-Amz-Security-Token=fake_token"
        "&X-Amz-Signature=fake_signature"
    )
    return url
