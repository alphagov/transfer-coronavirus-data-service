#!/usr/bin/env python


def get_group_list():
    groups = [
        {
            "preference": 10,
            "value": "standard-download",
            "display": "Standard download user",
        },
        {
            "preference": 20,
            "value": "standard-upload",
            "display": "Standard download and upload user",
        },
        {
            "preference": 70,
            "value": "admin-view",
            "display": "User administrator read-only",
        },
        {
            "preference": 80,
            "value": "admin-power",
            "display": "User administrator power (reinvite/disable)",
        },
        {
            "preference": 90,
            "value": "admin-full",
            "display": "User administrator full access",
        },
    ]
    return groups


def get_group_map():
    group_list = get_group_list()
    group_map = {group["value"]: group for group in group_list}
    return group_map


def get_group_by_name(group_name):
    group_map = get_group_map()
    return group_map[group_name]


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
