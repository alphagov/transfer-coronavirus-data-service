from cognito_groups import return_users_group, user_groups


fixture_standard_download = {
    "preference": 10,
    "value": "standard-download",
    "display": "Standard download user",
}

fixture_standard_upload = {
    "preference": 20,
    "value": "standard-upload",
    "display": "Standard download and upload user",
}


def test_user_groups():

    assert len(user_groups()) == 5

    bad_group = user_groups("admin")
    assert len(bad_group) == 1
    assert bad_group[0] == fixture_standard_download

    good_group = user_groups("standard-upload")
    assert len(good_group) == 1
    assert good_group[0] == fixture_standard_upload


def test_return_users_group():

    assert return_users_group() == fixture_standard_download
    assert return_users_group({}) == fixture_standard_download
    assert return_users_group({"groups": []}) == fixture_standard_download
    assert return_users_group({"groups": [""]}) == fixture_standard_download

    assert (
        return_users_group({"groups": ["standard-upload"]}) == fixture_standard_upload
    )
    assert (
        return_users_group({"groups": ["standard-download", "standard-upload"]})
        == fixture_standard_download
    )
    assert (
        return_users_group({"groups": ["standard-upload", "standard-download"]})
        == fixture_standard_download
    )
