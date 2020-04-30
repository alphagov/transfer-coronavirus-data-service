#!/usr/bin/env python

import csv
import os


def app_authorised_path():
    return os.getenv("BUCKET_MAIN_PREFIX", "web-app-prod-data")


# this list is from communitiesuk / MHCLG
# https://github.com/communitiesuk/c19-data-pipeline/blob/master/data/hub.csv
def hubs():
    res = []
    with open("hub.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            res.append({"hub": row["hub"], "name": row["name"]})
    return res


def valid_paths(input_path=None):
    res = []

    if input_path is None:
        input_path = app_authorised_path()

    other = [
        {"path": "other/gds", "disp": "GDS"},
        {"path": "other/nhs", "disp": "NHS"},
        {"path": "other/ons", "disp": "ONS"},
        {"path": "other/mhclg", "disp": "MHCLG"},
        {"path": "dwp-survey", "disp": "DWP Surveys"},
        {"path": "dwp", "disp": "DWP"},
        {"path": "dwp-upload-only", "disp": "DWP Upload Only"},
        {"path": "wholesaler/brakes", "disp": "Brakes"},
        {"path": "supermarket", "disp": "Supermarket"},
    ]
    res.append(
        {
            "type": "other",
            "main": "{}".format(input_path),
            "subs": [
                {"disp": d["disp"], "val": "{}/{}".format(input_path, d["path"])}
                for d in other
            ],
        }
    )

    la_hubs = hubs()
    res.append(
        {
            "type": "local_authority",
            "main": "{}/local_authority".format(input_path),
            "subs": [
                {
                    "disp": d["name"],
                    "val": "{}/local_authority/{}".format(input_path, d["hub"]),
                }
                for d in la_hubs
            ],
        }
    )

    return res


if __name__ == "__main__":
    print(valid_paths())
