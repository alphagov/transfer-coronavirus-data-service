import os
import re

from cognito import create_user, make_request
from cognito_groups import get_group_by_name, get_group_map
from logger import LOG


# This class represents a user and performs
# the necessary validations with cognito
class User:
    def __init__(self, email_address):
        self.email_address = (
            email_address.strip().lower().encode("latin1").decode("utf-8")
        )
        self.details = {}

    def name(self):
        return self.get_details().get("name", "")

    def phone_number(self):
        return self.get_details().get("phone_number", "")

    def phone_number_verified(self):
        return self.get_details().get("phone_number_verified", "")

    def __custom_paths_str(self):
        return self.get_details().get("custom:paths", "")

    def custom_paths(self):
        return self.__custom_paths_str().split(";") if self.__custom_paths_str() else []

    def created_at(self):
        return self.get_details().get("createdate", "")

    def modified_at(self):
        return self.get_details().get("lastmodifieddate", "")

    def enabled(self):
        return self.get_details().get("enabled", "")

    def status(self):
        return self.get_details().get("status", "")

    def group_name(self):
        return self.get_details().get("group", {}).get("value", "")

    def __is_la_str(self):
        return self.get_details().get("custom:is_la", "0")

    def is_la(self):
        return True if self.__is_la_str() == "1" else False

    """
    Create and set properties of cognito user

    Create user in cognito user pool
    If successful then:
    - Set MFA preference to SMS
    - Set MFA SMS phone number
    - Add user to the requested cognito group
    """

    def create(self, name, phone_number, custom_paths, is_la, group_name):
        phone_number = self.sanitise_phone(phone_number)
        if not self.email_address_is_valid():
            return False
        if phone_number == "":
            return False
        if not self.user_paths_are_valid(is_la, custom_paths, group_name):
            return False
        user_created = create_user(
            name, self.email_address, phone_number, is_la, custom_paths
        )

        if user_created:
            return True

        set_mfa = self.set_mfa_preferences()
        set_settings = self.set_user_settings()
        added_to_group = self.add_to_group(group_name)
        return set_mfa and set_settings and added_to_group

    def set_mfa_preferences(self):
        additional_arguments = {
            "SMSMfaSettings": {"Enabled": True, "PreferredMfa": True},
        }
        return make_request(
            "admin_set_user_mfa_preference", self.email_address, additional_arguments
        )

    def set_user_settings(self):
        additional_arguments = {
            "MFAOptions": [{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
        }
        return make_request(
            "admin_set_user_settings", self.email_address, additional_arguments
        )

    def add_to_group(self, group_name=None):
        if group_name is None:
            group_name = "standard-download"
        if group_name not in get_group_map().keys():
            return False

        return make_request(
            "admin_add_user_to_group", self.email_address, {"GroupName": group_name}
        )

    def set_group(self, new_group_name):
        if new_group_name is None:
            return
        if not isinstance(new_group_name, str):
            raise ValueError("ERR: %s: new_group_name is not str")

        group_name = self.details["group"]["value"]
        if group_name != new_group_name:
            make_request(
                "admin_remove_user_from_group",
                self.email_address,
                {"GroupName": group_name},
            )
            self.add_to_group(new_group_name)

    def sanitise_phone(self, phone_number):
        if phone_number != "":
            phone_number = re.sub(r"[^0-9]", "", phone_number)
            if phone_number.startswith("0"):
                phone_number = "+44" + phone_number[1:]
            if phone_number.startswith("44"):
                phone_number = "+44" + phone_number[2:]
            return phone_number
        return ""

    def sanitise_name(self, name):
        return re.sub(r"[^a-zA-Z0-9-_\']", "", name)

    def update(self, name, phone_number, custom_paths, is_la, group):
        if self.get_details() == {}:
            return False

        if (
            name is None
            and phone_number is None
            and custom_paths is None
            and is_la is None
            and group is None
        ):
            return False
        attrs = []
        try:
            attrs += self.__attribute("custom:is_la", is_la)
            attrs += self.__attribute("name", self.sanitise_name(name))
            attrs += self.__custom_path_attribute(is_la, custom_paths, group)
            attrs += self.__phone_number_attribute(phone_number)
            self.set_group(group)
        except ValueError:
            return False
        user_attributes = {}
        user_attributes["UserAttributes"] = attrs
        return make_request(
            "admin_update_user_attributes", self.email_address, user_attributes,
        )

    def __attribute(self, field_name, value):
        if value is None:
            return []

        if isinstance(value, str):
            return [{"Name": field_name, "Value": value}]
        else:
            raise ValueError(f"{value}: is not expected value for field: {field_name}")

    def __custom_path_attribute(self, is_la, custom_paths, group_name):
        if custom_paths is None:
            return []

        if isinstance(custom_paths, str):
            group_name = (
                group_name if group_name is not None else self.details["group"]["value"]
            )
            if not self.user_paths_are_valid(is_la, custom_paths, group_name):
                raise ValueError(f"custom paths: is not expected value")

            return [{"Name": "custom:paths", "Value": custom_paths}]
        else:
            raise ValueError(f"custom paths: is not expected value")

    def user_paths_are_valid(self, is_la, paths_semicolon_separated, group_name):
        if "admin" not in group_name and paths_semicolon_separated == "":
            return False

        app_authorised_paths = [os.getenv("BUCKET_MAIN_PREFIX", "web-app-prod-data")]
        for authorised_path in app_authorised_paths:
            for path in paths_semicolon_separated.split(";"):
                la_path = "{}/local_authority/".format(authorised_path)
                # if new attr for is_la is 0 (not a local authority)
                # then don't allow local_authority paths to be set
                if is_la == "0":
                    if path.startswith(la_path):
                        LOG.info("%s: won't set non-LA user to: %s" "user-admin", path)
                        return False
                # if new attr for is_la is 1 (IS local authority)
                # then only allow local_authority paths to be set
                if is_la == "1":
                    if not path.startswith(la_path):
                        LOG.info("%s: won't set LA user to: %s", "user-admin", path)
                        return False
        return True

    def __phone_number_attribute(self, phone_number):
        sanitised_phone = self.sanitise_phone(phone_number)
        phone_attribute = self.__attribute("phone_number", sanitised_phone)
        if sanitised_phone == self.details["phone_number"]:
            return phone_attribute
        else:
            return phone_attribute + [
                {"Name": "phone_number_verified", "Value": "false"}
            ]

    def delete(self):
        if not self.email_address_is_valid():
            LOG.error(
                "ERR: %s: the email %s is not valid", "user-admin", self.email_address
            )
            return False
        return make_request("admin_delete_user", self.email_address)

    def disable(self):
        if not self.email_address_is_valid():
            LOG.error(
                "ERR: %s: the email %s is not valid", "user-admin", self.email_address
            )
            return False
        return make_request("admin_disable_user", self.email_address)

    def enable(self):
        if not self.email_address_is_valid():
            LOG.error(
                "ERR: %s: the email %s is not valid", "user-admin", self.email_address
            )
            return False
        return make_request("admin_enable_user", self.email_address)

    def reinvite(self):
        if self.get_details() != {}:
            deleted = self.delete()
            if deleted:
                created = self.create(
                    self.name(),
                    self.phone_number(),
                    self.__custom_paths_str(),
                    self.__is_la_str(),
                    self.group_name(),
                )
                return created
        return False

    def get_details(self):
        if self.details == {}:
            aws_details = make_request("admin_get_user", self.email_address, {}, True)
            self.details = User.normalise(aws_details)
        return self.details

    def email_address_is_valid(self):
        return "@" in self.email_address and self.domain_is_allowed()

    def domain_is_allowed(self):
        for domain in self.allowed_domains():
            if self.email_address.endswith(domain):
                return True
        return False

    def allowed_domains(self):
        return [
            ".gov.uk",  # allow any *.gov.uk email
            "@brake.co.uk",  # allow @brake.co.uk (wholesaler)
            "@nhs.net",
            "@tesco.com",
            "@ocadoretail.com",
            "@morrisonsplc.co.uk",
            "@sainsburys.co.uk",
            "@iceland.co.uk",
            "@coop.co.uk",
            "@asda.co.uk",
            "@johnlewis.co.uk",
            "@capita.com",
            "@coreconsultants.io",
            "@antmarketing.com",
        ]

    @staticmethod
    def list(email_starts_filter="", token="", limit=20):
        arguments = {
            "AttributesToGet": [
                "name",
                "email",
                "email_verified",
                "phone_number",
                "phone_number_verified",
                "cognito:user_status",
                "custom:paths",
                "custom:is_la",
            ],
            "Limit": limit,
        }
        if email_starts_filter != "":
            arguments["Filter"] = 'email ^= "{}"'.format(email_starts_filter)
        if token != "":
            arguments["PaginationToken"] = token
        response = make_request("list_users", "", arguments, True)
        token = ""
        users = []
        if "Users" in response:
            for aws_user_details in response["Users"]:
                user = User.normalise(aws_user_details)
                if user != {}:
                    users.append(user)
            if "PaginationToken" in response:
                token = response["PaginationToken"]
            # Edge case where users could be blank but there is
            # a token for getting more users
            if not any(response["Users"]) and not token:
                return list(
                    email_starts_filter=email_starts_filter, limit=limit, token=token
                )
        return {"users": users, "token": token}

    @staticmethod
    def normalise(aws_details):
        result = {}
        if "Username" in aws_details:
            result = {
                "username": aws_details["Username"],
                "status": aws_details["UserStatus"],
                "createdate": aws_details["UserCreateDate"],
                "lastmodifieddate": aws_details["UserLastModifiedDate"],
                "enabled": aws_details["Enabled"],
            }
            for attr in aws_details[
                "Attributes" if "Attributes" in aws_details else "UserAttributes"
            ]:
                result[attr["Name"]] = attr["Value"]
        if "username" in result:
            result["group"] = User.group(result["username"])
        return result

    @staticmethod
    def group(username):
        response = make_request("admin_list_groups_for_user", username, {}, True)

        groups = []
        if "Groups" in response:
            for group in response["Groups"]:
                if "GroupName" in group:
                    groups.append(group["GroupName"])

        # Currently you can attach a list of users in cognito
        # but we're currently only interested in the first group
        group_name = None if len(groups) == 0 else groups[0]
        return get_group_by_name(group_name)
