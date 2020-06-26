import os

import pytest
from flask import Flask

import stubs
import config


def test_setup_talisman():
    app = Flask(__name__)
    config.set("app_environment", "testing")
    talisman = config.setup_talisman(app)
    assert not talisman.force_https

    app = Flask(__name__)
    config.set("app_environment", "staging")
    talisman = config.setup_talisman(app)
    assert talisman.force_https

    app = Flask(__name__)
    config.set("app_environment", "production")
    talisman = config.setup_talisman(app)
    assert talisman.force_https


def test_read_env_variables():
    app = Flask(__name__)
    config.read_env_variables(app)
    assert app.secret_key == os.getenv("APPSECRET", "secret")
    assert config.get("client_id") == os.getenv("CLIENT_ID", None)
    assert config.get("cognito_domain") == os.getenv("COGNITO_DOMAIN", None)
    assert config.get("client_secret") == os.getenv("CLIENT_SECRET", None)
    assert config.get("redirect_host") == os.getenv("REDIRECT_HOST")
    assert config.get("bucket_name") == os.getenv("BUCKET_NAME")
    assert config.get("region") == os.getenv("REGION")


@pytest.mark.usefixtures("test_ssm_parameters")
def test_load_ssm_parameters(test_ssm_parameters):
    app = Flask(__name__)
    path = "/transfer-coronavirus-data-service"
    stubber = stubs.mock_config_load_ssm_parameters(path, test_ssm_parameters)
    with stubber:
        config.load_ssm_parameters(app)
        assert (
            config.get("cognito_pool_name") == test_ssm_parameters["/cognito/pool/name"]
        )
        assert config.get("cognito_pool_id") == test_ssm_parameters["/cognito/pool/id"]
        assert config.get("bucket_name") == test_ssm_parameters["/s3/bucket_name"]
        assert config.get("bucket_main_prefix") == test_ssm_parameters["/s3/bucket_main_prefix"]
        stubber.deactivate()


@pytest.mark.usefixtures("test_load_cognito_settings")
def test_set_app_settings(test_load_cognito_settings):
    stubber = stubs.mock_config_set_app_settings(test_load_cognito_settings)
    with stubber:
        config.delete("client_id")
        config.load_cognito_settings()
        assert config.get("client_id") == test_load_cognito_settings["client_id"]
        assert (
            config.get("client_secret") == test_load_cognito_settings["client_secret"]
        )
        cognito_domain = (
            f"{test_load_cognito_settings['host_name']}."
            f"{test_load_cognito_settings['domain']}"
        )
        assert config.get("cognito_domain") == cognito_domain
        stubber.deactivate()


def test_list_pools():
    user_pool_id = stubs.MOCK_COGNITO_USER_POOL_ID
    stubber = stubs.mock_cognito_list_pools()

    with stubber:
        pools = config.list_pools()
        assert pools[0]["id"] == user_pool_id
        stubber.deactivate()
