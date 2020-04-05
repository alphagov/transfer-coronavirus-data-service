from cognito_groups import return_users_group, user_groups


fx_standard_download = {
    "preference": 10,
    "value": "standard-download",
    "display": "Standard download user",
}

fx_standard_upload = {
    "preference": 20,
    "value": "standard-upload",
    "display": "Standard download and upload user",
}


def test_user_groups():

    assert len(user_groups()) == 5

    bad_group = user_groups("admin")
    assert len(bad_group) == 1
    assert bad_group[0] == fx_standard_download

    good_group = user_groups("standard-upload")
    assert len(good_group) == 1
    assert good_group[0] == fx_standard_upload


def test_return_users_group():

    assert return_users_group() == fx_standard_download
    assert return_users_group({}) == fx_standard_download
    assert return_users_group({"group": []}) == fx_standard_download
    assert return_users_group({"group": [""]}) == fx_standard_download

    assert return_users_group({"group": "standard-upload"}) == fx_standard_upload
    assert return_users_group({"group": "standard-download"}) == fx_standard_download
