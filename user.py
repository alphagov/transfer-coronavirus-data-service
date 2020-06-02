import re

import cognito
from cognito_groups import get_group_by_name
import config
from logger import LOG


# This class represents a user and performs
# the necessary validations with cognito
class User:
    def __init__(self, email_address):
        self.email_address = (
            email_address.strip().lower().encode("latin1").decode("utf-8")
        )
        self.details = {}
        self.cognito_client = cognito.get_boto3_client()

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
        """
        Create a new user in Cognito user pool

        Validate the inputs.
        A user is only valid if their MFA and group settings
        are correct.
        Return True only if all steps are processed successfully.
        """
        error = None
        steps = {}

        # Validate email
        if not self.email_address_is_valid():
            steps["email_valid"] = False
            error = "Email address is invalid."

        # Validate phone number
        phone_number = self.sanitise_phone(phone_number)
        if phone_number == "":
            steps["phone_valid"] = False
            error = "Phone number is empty."

        # Validate user custom settings
        if not self.user_paths_are_valid(is_la, custom_paths, group_name):
            steps["paths_valid"] = False
            error = "The granted access permissions are not valid."

        # Only attempt create if all previous steps passed
        if all(steps.values()):
            steps["created"] = cognito.create_user(
                name, self.email_address, phone_number, is_la, custom_paths
            )

        if steps.get("created"):
            steps["set_mfa"] = self.set_mfa_preferences()
            steps["set_settings"] = self.set_user_settings()
            steps["added_to_group"] = self.add_to_group(group_name)
        else:
            error = "Failed to create user."

        if error:
            config.set_session_var("error_message", error)
            LOG.error(
                {
                    "message": "User operation failed",
                    "action": "user.create",
                    "status": steps,
                }
            )
        # Return True only if all settings were successfully set
        return all(steps.values())

    def set_mfa_preferences(self):
        is_set = cognito.set_mfa_preferences(self.email_address)
        if not is_set:
            config.set_session_var("error_message", "Failed to set MFA preferences.")
        return is_set

    def set_user_settings(self):
        is_set = cognito.set_user_settings(self.email_address)
        if not is_set:
            config.set_session_var(
                "error_message", "Failed to set preferred MFA to mobile."
            )
        return is_set

    def add_to_group(self, group_name=None):
        is_set = cognito.add_to_group(self.email_address, group_name)
        if not is_set:
            config.set_session_var(
                "error_message", f"Failed to add user to {group_name} group."
            )
        return is_set

    def set_group(self, new_group_name):
        if new_group_name is None:
            return
        if not isinstance(new_group_name, str):
            raise ValueError("ERR: %s: new_group_name is not str")

        current_group_name = self.details["group"]["value"]
        if current_group_name != new_group_name:
            removed = cognito.remove_from_group(self.email_address, current_group_name)
            if removed:
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
        """
        Validate the input fields and existing user settings.

        Perform update only if all validation steps pass.
        Return True only if all steps pass.
        """

        error = None
        steps = {}

        # Check user exists
        steps["user_found"] = self.get_details() == {}
        if not steps.get("user_found"):
            error = "Failed to get user details to update."

        # Check input parameters are all set
        steps["inputs_valid"] = (
            name is None
            and phone_number is None
            and custom_paths is None
            and is_la is None
            and group is None
        )
        if not steps.get("inputs_valid"):
            error = "The new value for a field is missing or blank."

        # Check the earlier steps have passed
        if all(steps.values()):
            user_attributes = []
            try:
                user_attributes += self.__attribute("custom:is_la", is_la)
                user_attributes += self.__attribute("name", self.sanitise_name(name))
                user_attributes += self.__custom_path_attribute(
                    is_la, custom_paths, group
                )
                user_attributes += self.__phone_number_attribute(phone_number)
                self.set_group(group)
            except ValueError:
                error = "The current value for a field is missing or blank."
                steps["current_valid"] = False

        # If all tests have passed try the update
        if all(steps.values()):
            steps["updated"] = cognito.update_user(self.email_address, user_attributes)
            if not steps.get("updated"):
                error = "The fields were valid but the user failed to update."

        if error:
            config.set_session_var("error_message", error)
            LOG.error(
                {
                    "message": "User operation failed",
                    "action": "user.update",
                    "status": steps,
                }
            )

        # Return True if valid and updated
        return all(steps.values())

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
                raise ValueError("custom paths: is not expected value")

            return [{"Name": "custom:paths", "Value": custom_paths}]
        else:
            raise ValueError("custom paths: is not expected value")

    def user_paths_are_valid(self, is_la, paths_semicolon_separated, group_name):

        all_user_paths_are_valid = True

        # All non-admin users should have a non-empty path in custom:paths
        if "admin" not in group_name and paths_semicolon_separated == "":
            LOG.error(
                {
                    "user": self.email_address,
                    "group": group_name,
                    "message": "Path is missing for non-admin user",
                }
            )
            all_user_paths_are_valid = False

        app_authorised_paths = [config.get("bucket_main_prefix", "web-app-prod-data")]

        user_authorised_paths = paths_semicolon_separated.split(";")

        # Local Authority users: is_la = 1
        # can only be granted access to [main_prefix]/local_authority/* paths
        # Non Local Authority users: is_la = 0
        # can only be granted access to [main_prefix]/other/* paths
        for authorised_path in app_authorised_paths:
            for path in user_authorised_paths:
                la_path = "{}/local_authority/".format(authorised_path)
                user_is_local_authority = is_la == "1"
                path_is_local_authority = path.startswith(la_path)
                if user_is_local_authority != path_is_local_authority:
                    LOG.error(
                        {
                            "user": self.email_address,
                            "group": group_name,
                            "path": path,
                            "is_la": is_la,
                            "message": "Path is invalid for user type",
                        }
                    )
                    all_user_paths_are_valid = False

        return all_user_paths_are_valid

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
        return cognito.delete_user(self.email_address)

    def disable(self):
        if not self.email_address_is_valid():
            LOG.error(
                "ERR: %s: the email %s is not valid", "user-admin", self.email_address
            )
            return False
        return cognito.disable_user(self.email_address)

    def enable(self):
        if not self.email_address_is_valid():
            LOG.error(
                "ERR: %s: the email %s is not valid", "user-admin", self.email_address
            )
            return False
        return cognito.enable_user(self.email_address)

    def reinvite(self):
        details = self.get_details()
        if details != {}:
            LOG.debug(details)
            deleted = self.delete()
            LOG.debug({"action": "delete", "status": deleted})
            if deleted:

                created = self.create(
                    self.name(),
                    self.phone_number(),
                    self.__custom_paths_str(),
                    self.__is_la_str(),
                    self.group_name(),
                )
                LOG.debug({"action": "create", "status": created})
                return created
        return False

    def get_details(self):
        if self.details == {}:
            aws_details = cognito.get_user(self.email_address)
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
        cognito_client = cognito.get_boto3_client()
        response = cognito_client.list_users(**arguments)
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
        response = cognito.list_groups_for_user(username)

        groups = []
        if "Groups" in response:
            for group in response["Groups"]:
                if "GroupName" in group:
                    groups.append(group["GroupName"])

        # Currently you can attach a list of users in cognito
        # but we're currently only interested in the first group
        group_name = None if len(groups) == 0 else groups[0]

        LOG.debug("User group returns: %s", group_name)
        return get_group_by_name(group_name)
