# """ Create mock boto3 clients for testing """
from datetime import datetime

import boto3
from botocore.stub import Stubber

from logger import LOG

MOCK_COGNITO_USER_POOL_ID = "eu-west-2_poolid"


def _keep_it_real():
    """ Keep the native """
    if not getattr(boto3, "real_client", None):
        boto3.real_client = boto3.client


def mock_s3_list_objects(bucket_name, prefixes, is_upload=False):
    _keep_it_real()
    client = boto3.real_client("s3")

    stubber = Stubber(client)

    for prefix in prefixes:
        if is_upload:
            stub_response_s3_list_upload_objects_page_1(stubber, bucket_name, prefix)
            stub_response_s3_list_upload_objects_page_2(stubber, bucket_name, prefix)
        else:
            stub_response_s3_list_objects_page_1(stubber, bucket_name, prefix)
            stub_response_s3_list_objects_page_2(stubber, bucket_name, prefix)

    # replace the get_presigned_url so it runs without AWS creds
    client.generate_presigned_url = lambda op, Params, ExpiresIn, HttpMethod: fake_url(
        Params["Bucket"], Params["Key"]
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name, config=None: client
    return stubber


# Module: main.py
def mock_cognito_auth_flow(token, test_user):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_get_user(stubber, token, test_user)
    stub_response_cognito_admin_list_groups_for_user(stubber, test_user["Username"])

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


# Module: cognito.py
def mock_cognito_create_user(admin_user, create_user_arguments):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    group_name = admin_user["group"]["value"]

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_create_user(stubber, admin_user, create_user_arguments)
    stub_response_cognito_admin_set_user_mfa_preference(stubber, admin_user["email"])
    stub_response_cognito_admin_set_user_settings(stubber, admin_user["email"])
    stub_response_cognito_admin_add_user_to_group(
        stubber, admin_user["email"], group_name
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_create_user_set_mfa_fails(admin_user, create_user_arguments):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    group_name = admin_user["group"]["value"]

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_create_user(stubber, admin_user, create_user_arguments)
    # Replace admin_set_user_mfa_preference response with ClientError
    # stub_response_cognito_admin_set_user_mfa_preference(stubber, admin_user["email"])
    stubber.add_client_error(
        "admin_set_user_mfa_preference",
        expected_params={
            "SMSMfaSettings": {"Enabled": True, "PreferredMfa": True},
            "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
            "Username": admin_user["email"],
        },
    )
    stub_response_cognito_admin_set_user_settings(stubber, admin_user["email"])
    stub_response_cognito_admin_add_user_to_group(
        stubber, admin_user["email"], group_name
    )
    stub_response_cognito_admin_disable_user(stubber, admin_user["email"])

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_create_user_set_user_settings_fails(admin_user, create_user_arguments):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    group_name = admin_user["group"]["value"]

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_create_user(stubber, admin_user, create_user_arguments)
    stub_response_cognito_admin_set_user_mfa_preference(stubber, admin_user["email"])
    # stub_response_cognito_admin_set_user_settings(stubber, admin_user["email"])
    stubber.add_client_error(
        "admin_set_user_settings",
        expected_params={
            "MFAOptions": [{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
            "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
            "Username": admin_user["email"],
        },
    )

    stub_response_cognito_admin_add_user_to_group(
        stubber, admin_user["email"], group_name
    )
    stub_response_cognito_admin_disable_user(stubber, admin_user["email"])

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_create_user_add_user_to_group_fails(admin_user, create_user_arguments):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    group_name = admin_user["group"]["value"]

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_create_user(stubber, admin_user, create_user_arguments)
    stub_response_cognito_admin_set_user_mfa_preference(stubber, admin_user["email"])
    stub_response_cognito_admin_set_user_settings(stubber, admin_user["email"])

    # stub_response_cognito_admin_add_user_to_group(
    #     stubber, admin_user["email"], group_name
    # )
    stubber.add_client_error(
        "admin_add_user_to_group",
        expected_params={
            "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
            "Username": admin_user["email"],
            "GroupName": group_name,
        },
    )
    stub_response_cognito_admin_disable_user(stubber, admin_user["email"])

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_list_pools(env="dev-four"):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_list_user_pools(stubber, env)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_create_user(user, arguments):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")
    params_admin_create_user = {
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        "Username": user["email"],
        **arguments,
    }

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_create_user(stubber, user, params_admin_create_user)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_update_user_attributes(user, attributes):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_update_user_attributes(
        stubber, user["email"], attributes
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_delete_user(email):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_delete_user(stubber, email)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_disable_user(email):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_disable_user(stubber, email)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_enable_user(email):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_enable_user(stubber, email)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_set_user_settings(email):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_set_user_settings(stubber, email)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_set_user_mfa_preference(email):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    stub_response_cognito_admin_set_user_mfa_preference(stubber, email)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_add_user_to_group(email, group_name):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_add_user_to_group(stubber, email, group_name)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_remove_user_from_group(email, group_name):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_remove_user_from_group(stubber, email, group_name)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_get_user(email, admin_get_user):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_get_user(stubber, email, admin_get_user)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_cognito_admin_list_groups_for_user(admin_user):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_list_groups_for_user(stubber, admin_user["email"])

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


# Module: user.py
def mock_user_get_details(email, admin_get_user):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_get_user(stubber, email, admin_get_user)
    stub_response_cognito_admin_list_groups_for_user(stubber, email)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_user_not_found(email):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stubber.add_client_error(
        "admin_get_user",
        expected_params={"UserPoolId": MOCK_COGNITO_USER_POOL_ID, "Username": email},
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_user_update(email, admin_get_user, attributes):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_admin_get_user(stubber, email, admin_get_user)
    stub_response_cognito_admin_list_groups_for_user(stubber, email)
    stub_response_cognito_admin_update_user_attributes(stubber, email, attributes)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_user_reinvite(admin_user, admin_get_user, create_user_arguments):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    group_name = admin_user["group"]["value"]

    stubber = Stubber(client)

    # Add responses
    # get user
    stub_response_cognito_admin_get_user(stubber, admin_user["email"], admin_get_user)
    stub_response_cognito_admin_list_groups_for_user(stubber, admin_user["email"])

    # delete user
    stub_response_cognito_admin_delete_user(stubber, admin_user["email"])

    # create user
    stub_response_cognito_admin_create_user(stubber, admin_user, create_user_arguments)
    stub_response_cognito_admin_set_user_mfa_preference(stubber, admin_user["email"])
    stub_response_cognito_admin_set_user_settings(stubber, admin_user["email"])
    stub_response_cognito_admin_add_user_to_group(
        stubber, admin_user["email"], group_name
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_delete_user_failure(admin_user, admin_get_user):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    # get user
    stub_response_cognito_admin_get_user(stubber, admin_user["email"], admin_get_user)
    stub_response_cognito_admin_list_groups_for_user(stubber, admin_user["email"])

    # delete user
    stubber.add_client_error(
        "admin_delete_user",
        expected_params={
            "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
            "Username": admin_user["email"],
        },
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_create_user_failure(admin_user, admin_get_user, create_user_arguments):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    # get user
    stub_response_cognito_admin_get_user(stubber, admin_user["email"], admin_get_user)
    stub_response_cognito_admin_list_groups_for_user(stubber, admin_user["email"])

    # delete user
    stub_response_cognito_admin_delete_user(stubber, admin_user["email"])

    # create user
    stubber.add_client_error(
        "admin_create_user", expected_params=create_user_arguments,
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_config_set_app_settings(parameters):
    _keep_it_real()
    client = boto3.real_client("cognito-idp")

    stubber = Stubber(client)

    # Add responses
    stub_response_cognito_list_user_pool_clients(stubber, parameters)
    stub_response_cognito_describe_user_pool_client(stubber, parameters)
    stub_response_cognito_describe_user_pool(stubber, parameters)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


def mock_config_load_ssm_parameters(path, parameters):
    _keep_it_real()
    client = boto3.real_client("ssm")

    stubber = Stubber(client)

    # Add responses
    stub_response_ssm_get_parameters_by_path(stubber, path, parameters)

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service, region_name=None: client
    return stubber


# Responses
# Client: ssm
def stub_response_ssm_get_parameters_by_path(stubber, path, parameters):
    response_params = [
        {"Name": f"{path}{param_name}", "Value": param_value}
        for param_name, param_value in parameters.items()
    ]
    mock_get_parameters_by_path = {"Parameters": response_params}
    parameters = {"Path": path, "Recursive": True, "WithDecryption": True}

    stubber.add_response(
        "get_parameters_by_path", mock_get_parameters_by_path, parameters
    )


# Client: s3
def stub_response_s3_list_objects_page_1(stubber, bucket_name, prefix):
    now = datetime.utcnow()
    mock_list_objects_1 = {
        "Contents": [
            {"Key": f"{prefix}/people1.csv", "Size": 100, "LastModified": now},
            {"Key": f"{prefix}/people2.csv", "Size": 200, "LastModified": now},
            {
                "Key": f"{prefix}/nested/nested_people1.csv",
                "Size": 300,
                "LastModified": now,
            },
        ],
        "IsTruncated": True,
        "NextMarker": "page-2",
    }

    stubber.add_response(
        "list_objects", mock_list_objects_1, {"Bucket": bucket_name, "Prefix": prefix},
    )


def stub_response_s3_list_objects_page_2(stubber, bucket_name, prefix):
    now = datetime.utcnow()
    mock_list_objects_2 = {
        "Contents": [
            {"Key": f"{prefix}/people3.csv", "Size": 100, "LastModified": now},
            {"Key": f"{prefix}/people4.csv", "Size": 200, "LastModified": now},
        ]
    }

    stubber.add_response(
        "list_objects",
        mock_list_objects_2,
        {"Bucket": bucket_name, "Prefix": prefix, "Marker": "page-2"},
    )


def stub_response_s3_list_upload_objects_page_1(stubber, bucket_name, prefix):
    now = datetime.utcnow()
    mock_list_objects_1 = {
        "Contents": [
            {"Key": f"{prefix}/people1.csv", "Size": 100, "LastModified": now},
            {
                "Key": f"{prefix}/people1.csv-metadata.json",
                "Size": 100,
                "LastModified": now,
            },
            {"Key": f"{prefix}/people2.csv", "Size": 200, "LastModified": now},
            {
                "Key": f"{prefix}/people2.csv-metadata.json",
                "Size": 200,
                "LastModified": now,
            },
            {
                "Key": f"{prefix}/nested/nested_people1.csv",
                "Size": 300,
                "LastModified": now,
            },
            {
                "Key": f"{prefix}/nested/nested_people1.csv-metadata.json",
                "Size": 300,
                "LastModified": now,
            },
        ],
        "IsTruncated": True,
        "NextMarker": "page-2",
    }

    stubber.add_response(
        "list_objects", mock_list_objects_1, {"Bucket": bucket_name, "Prefix": prefix},
    )


def stub_response_s3_list_upload_objects_page_2(stubber, bucket_name, prefix):
    now = datetime.utcnow()
    mock_list_objects_2 = {
        "Contents": [
            {"Key": f"{prefix}/people3.csv", "Size": 100, "LastModified": now},
            {
                "Key": f"{prefix}/people3.csv-metadata.json",
                "Size": 100,
                "LastModified": now,
            },
            {"Key": f"{prefix}/people4.csv", "Size": 200, "LastModified": now},
            {
                "Key": f"{prefix}/people4.csv-metadata.json",
                "Size": 200,
                "LastModified": now,
            },
        ]
    }

    stubber.add_response(
        "list_objects",
        mock_list_objects_2,
        {"Bucket": bucket_name, "Prefix": prefix, "Marker": "page-2"},
    )


# Client: cognito-idp
def stub_response_cognito_list_user_pools(stubber, env="dev-four"):
    mock_list_user_pools = {
        "UserPools": [
            {"Id": MOCK_COGNITO_USER_POOL_ID, "Name": f"corona-cognito-pool-{env}"}
        ]
    }
    LOG.debug(mock_list_user_pools)
    stubber.add_response("list_user_pools", mock_list_user_pools, {"MaxResults": 10})


def stub_response_cognito_list_user_pool_clients(
    stubber, parameters, env="development"
):
    mock_list_user_pools = {
        "UserPoolClients": [
            {
                "ClientId": parameters["client_id"],
                "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
                "ClientName": f"corona-cognito-pool-{env}-client",
            }
        ]
    }
    params = {"UserPoolId": MOCK_COGNITO_USER_POOL_ID, "MaxResults": 2}
    stubber.add_response("list_user_pool_clients", mock_list_user_pools, params)


def stub_response_cognito_describe_user_pool_client(stubber, parameters):

    mock_describe_user_pool_client = {
        "UserPoolClient": {
            "ClientSecret": parameters["client_secret"],
            "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        }
    }
    params = {
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        "ClientId": parameters["client_id"],
    }
    stubber.add_response(
        "describe_user_pool_client", mock_describe_user_pool_client, params
    )


def stub_response_cognito_describe_user_pool(stubber, parameters):
    mock_describe_user_pool = {
        "UserPool": {"Domain": parameters["host_name"], "EstimatedNumberOfUsers": 12}
    }
    params = {"UserPoolId": MOCK_COGNITO_USER_POOL_ID}
    stubber.add_response("describe_user_pool", mock_describe_user_pool, params)


def stub_response_cognito_get_user(stubber, token, mock_get_user):
    stubber.add_response("get_user", mock_get_user, {"AccessToken": token})


def stub_response_cognito_admin_get_user(stubber, email, response):
    mock_admin_get_user = response

    params_admin_get_user = {"UserPoolId": MOCK_COGNITO_USER_POOL_ID, "Username": email}

    stubber.add_response(
        "admin_get_user", mock_admin_get_user, params_admin_get_user,
    )


def stub_response_cognito_admin_list_groups_for_user(stubber, email):
    now = datetime.utcnow()
    mock_admin_list_groups_for_user = {
        "Groups": [
            {
                "GroupName": "standard-download",
                "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
                "Description": "Standard download user",
                "Precedence": 10,
                "LastModifiedDate": now,
                "CreationDate": now,
            }
        ]
    }
    stubber.add_response(
        "admin_list_groups_for_user",
        mock_admin_list_groups_for_user,
        {"UserPoolId": MOCK_COGNITO_USER_POOL_ID, "Username": email},
    )


def stub_response_cognito_admin_create_user(stubber, admin_user, create_user_arguments):
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


def stub_response_cognito_admin_set_user_mfa_preference(stubber, email):
    mock_admin_set_user_mfa_preference = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    params_admin_set_user_mfa_preference = {
        "SMSMfaSettings": {"Enabled": True, "PreferredMfa": True},
        "Username": email,
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
    }

    stubber.add_response(
        "admin_set_user_mfa_preference",
        mock_admin_set_user_mfa_preference,
        params_admin_set_user_mfa_preference,
    )


def stub_response_cognito_admin_set_user_settings(stubber, email):
    mock_admin_set_user_settings = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    params_admin_set_user_settings = {
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        "Username": email,
        "MFAOptions": [{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
    }

    stubber.add_response(
        "admin_set_user_settings",
        mock_admin_set_user_settings,
        params_admin_set_user_settings,
    )


def stub_response_cognito_admin_add_user_to_group(stubber, email, group_name):
    mock_admin_add_user_to_group = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    params_admin_add_user_to_group = {
        "Username": email,
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        "GroupName": group_name,
    }
    stubber.add_response(
        "admin_add_user_to_group",
        mock_admin_add_user_to_group,
        params_admin_add_user_to_group,
    )


def stub_response_cognito_admin_update_user_attributes(stubber, email, attributes):
    mock_admin_update_user_attributes = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    params_admin_update_user_attributes = {
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        "Username": email,
        "UserAttributes": attributes,
    }

    stubber.add_response(
        "admin_update_user_attributes",
        mock_admin_update_user_attributes,
        params_admin_update_user_attributes,
    )


def stub_response_cognito_admin_delete_user(stubber, email):
    mock_admin_delete_user = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    params_admin_delete_user = {
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        "Username": email,
    }

    stubber.add_response(
        "admin_delete_user", mock_admin_delete_user, params_admin_delete_user,
    )


def stub_response_cognito_admin_disable_user(stubber, email):
    mock_admin_disable_user = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    params_admin_disable_user = {
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        "Username": email,
    }

    stubber.add_response(
        "admin_disable_user", mock_admin_disable_user, params_admin_disable_user,
    )


def stub_response_cognito_admin_enable_user(stubber, email):
    mock_admin_enable_user = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    params_admin_enable_user = {
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        "Username": email,
    }

    stubber.add_response(
        "admin_enable_user", mock_admin_enable_user, params_admin_enable_user,
    )


def stub_response_cognito_admin_remove_user_from_group(stubber, email, group_name):
    mock_admin_remove_user_from_group = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    params_admin_remove_user_from_group = {
        "UserPoolId": MOCK_COGNITO_USER_POOL_ID,
        "Username": email,
        "GroupName": group_name,
    }

    stubber.add_response(
        "admin_remove_user_from_group",
        mock_admin_remove_user_from_group,
        params_admin_remove_user_from_group,
    )


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
