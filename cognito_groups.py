#!/usr/bin/env python


def get_group_list():
    group_map = get_group_map()
    groups = group_map.values()
    return groups


def get_group_map():
    groups = {
        "standard-download": {
            "preference": 10,
            "value": "standard-download",
            "display": "Standard download user",
        },
        "standard-upload": {
            "preference": 20,
            "value": "standard-upload",
            "display": "Standard download and upload user",
        },
        "admin-view": {
            "preference": 70,
            "value": "admin-view",
            "display": "User administrator read-only",
        },
        "admin-power": {
            "preference": 80,
            "value": "admin-power",
            "display": "User administrator power (reinvite/disable)",
        },
        "admin-full": {
            "preference": 90,
            "value": "admin-full",
            "display": "User administrator full access",
        },
    }
    return groups


def get_group_by_name(group_name):
    if group_name is None:
        group_name = "standard-download"
    return get_group_map()[group_name]


def user_groups(group_value=None):
    groups = get_group_list()

    if group_value is not None:
        for group in groups:
            if group_value == group["value"]:
                return [group]
        return user_groups("standard-download")

    return groups


def return_users_group(user=None):
    """
    Return the users current group or the default
    group for new users if not specified
    """

    default_group_name = "standard-download"
    group_map = get_group_map()
    default_group = group_map[default_group_name]
    try:
        group = user.get("group", default_group)
    except (ValueError, KeyError, AttributeError):
        group = default_group
    return group
