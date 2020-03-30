""" Declare a logger to be used by any module """
import datetime
import json
import logging
import os
import sys


class JsonFormatter(logging.Formatter):
    """ Handle log invokes with string, dict or json.dumps """

    def format(self):
        """ Detect formatting of self message and encode as valid JSON """
        data = {}
        data.update(vars(self))
        try:
            json.loads(self.msg)
            parsed = json.loads(self.msg)
            if type(parsed) in [dict, list]:
                data["msg"] = parsed
        except (ValueError, TypeError, json.JSONDecodeError):
            pass

        try:
            if ("args" in data) and len(data["args"]) > 0:
                args = data["args"]
                data["msg"] = data["msg"] % args
        except TypeError:
            pass

        data["timestamp"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        try:
            log_message = json.dumps(data, default=str)
        except (TypeError, ValueError) as err:
            log_message = str(err)
        return log_message


def build_logger(log_name, log_level="ERROR"):
    """ Create shared logger and custom JSON handler """
    logger = logging.getLogger(log_name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter)
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, log_level))
    return logger


LOG_LEVEL = str(os.getenv("LOG_LEVEL", "ERROR"))
LOG = build_logger("vulnerable_people_data_service", log_level=LOG_LEVEL)
