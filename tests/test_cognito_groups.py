import pytest

from cognito_groups import return_users_group, user_groups


@pytest.mark.usefixtures("standard_download")
@pytest.mark.usefixtures("standard_upload")
def test_user_groups(standard_download, standard_upload):

    assert len(user_groups()) == 5

    bad_group = user_groups("admin")
    assert len(bad_group) == 1
    assert bad_group[0] == standard_download

    good_group = user_groups("standard-upload")
    assert len(good_group) == 1
    assert good_group[0] == standard_upload


@pytest.mark.usefixtures("standard_download")
@pytest.mark.usefixtures("standard_upload")
def test_return_users_group(standard_download, standard_upload):

    assert return_users_group() == standard_download
    assert return_users_group({}) == standard_download
    assert return_users_group({"group": []}) == standard_download
    assert return_users_group({"group": [""]}) == standard_download

    assert return_users_group({"group": "standard-upload"}) == standard_upload
    assert return_users_group({"group": "standard-download"}) == standard_download
