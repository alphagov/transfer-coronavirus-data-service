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
        for g in groups:
            if groupvalue == g["value"]:
                return [g]
        return user_groups("standard-download")

    return groups


def return_users_group(user=None):
    sel_group = user_groups("standard-download")[0]

    start_pref = 1000
    if user is not None and "groups" in user:
        avail_groups = user_groups()
        for ug in user["groups"]:
            for ag in avail_groups:
                if ug == ag["value"] and ag["preference"] < start_pref:
                    sel_group = ag
                    start_pref = ag["preference"]

    return sel_group
