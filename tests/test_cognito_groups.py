import pytest

from cognito_groups import (
    get_group_by_name,
    get_group_list,
    get_group_map,
    return_users_group,
    user_groups,
)


@pytest.mark.usefixtures("standard_download")
@pytest.mark.usefixtures("standard_upload")
def test_get_group_map(standard_download, standard_upload):

    group_map = get_group_map()
    assert len(group_map.keys()) == 5
    assert group_map["standard-download"] == standard_download
    assert group_map["standard-upload"] == standard_upload


@pytest.mark.usefixtures("standard_download")
@pytest.mark.usefixtures("standard_upload")
def test_get_group_list(standard_download, standard_upload):

    group_list = get_group_list()

    assert len(group_list) == 5
    assert standard_download in group_list
    assert standard_upload in group_list


@pytest.mark.usefixtures("standard_download")
@pytest.mark.usefixtures("standard_upload")
def test_get_group_by_name(standard_download, standard_upload):

    group = get_group_by_name("standard-download")
    assert group == standard_download

    group = get_group_by_name("standard-upload")
    assert group == standard_upload


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

    assert return_users_group({"group": standard_upload}) == standard_upload
    assert return_users_group({"group": standard_download}) == standard_download
