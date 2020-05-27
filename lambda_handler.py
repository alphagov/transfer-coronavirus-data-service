import os

import serverless_wsgi

from main import app
from config import load_environment, setup_talisman


def web_app(event, context):
    """Lambda handler entry point for web app.
        :param event: An event from an ALB
        :param context: An AWS context object
        :returns: An AWS ALB event
        :rtype: dict
    """
    return run(event, context)


def admin(event, context):
    """Lambda handler entry point for admin app.
    Designates the environment as ADMIN.
    Ensures correct user management: admin users cannot upload or download objects from S3
    but do have permission to edit the cognito pool.
        :param event: An event from an ALB
        :param context: An AWS context object
        :returns: An AWS ALB event
        :rtype: dict
    """
    os.environ["ADMIN"] = "true"
    return run(event, context)


def run(event, context):
    setup_talisman(app)
    load_environment(app)
    return serverless_wsgi.handle_request(app, event, context)
