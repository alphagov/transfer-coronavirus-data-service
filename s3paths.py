#!/usr/bin/env python

import csv
import os


def app_authorised_paths():
    return [os.getenv("BUCKET_MAIN_PREFIX", "web-app-prod-data")]


# this list is from communitiesuk / MHCLG
# https://github.com/communitiesuk/c19-data-pipeline/blob/master/data/hub.csv
def hubs():
    res = []
    with open("hub.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            res.append({"hub": row["hub"], "name": row["name"]})
    return res


def valid_paths():
    res = []

    for auth_path in app_authorised_paths():
        res.append({"type": "dwp", "main": "{}/dwp".format(auth_path), "subs": []})

        wholesalers = ["brakes"]
        res.append(
            {
                "type": "wholesaler",
                "main": "{}/wholesaler".format(auth_path),
                "subs": [
                    {"disp": d.upper(), "val": "{}/wholesaler/{}".format(auth_path, d)}
                    for d in wholesalers
                ],
            }
        )

        la_hubs = hubs()
        res.append(
            {
                "type": "local_authority",
                "main": "{}/local_authority".format(auth_path),
                "subs": [
                    {
                        "disp": d["name"],
                        "val": "{}/local_authority/{}".format(auth_path, d["hub"]),
                    }
                    for d in la_hubs
                ],
            }
        )

    return res


if __name__ == "__main__":
    print(valid_paths())
