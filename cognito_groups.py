#!/usr/bin/env python


def user_groups(groupvalue=None):
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

    if groupvalue is not None:
        for group in groups:
            if groupvalue == group["value"]:
                return [group]
        return user_groups("standard-download")

    return groups


def return_users_group(user=None):
    sel_group = user_groups("standard-download")[0]

    if user is not None and "group" in user:
        for group in user_groups():
            if user["group"] == group["value"]:
                sel_group = group
                break

    return sel_group
