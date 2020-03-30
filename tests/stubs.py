""" Create mock boto3 clients for testing """

import boto3
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


def mock_cognito(token):
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

    stubber.add_response(
        "get_user", mock_get_user, {"AccessToken": token},
    )

    stubber.activate()
    # override boto.client to return the mock client
    boto3.client = lambda service: client
    return stubber
