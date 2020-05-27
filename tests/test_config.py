import os

from flask import Flask

import stubs
from config import (
    load_environment,
    setup_talisman,
    list_pools,
    env_pool_id,
    get_cognito_pool_name,
)


def test_setup_talisman():
    app = Flask(__name__)
    app.app_environment = "testing"
    talisman = setup_talisman(app)
    assert not talisman.force_https

    app = Flask(__name__)
    app.app_environment = "staging"
    talisman = setup_talisman(app)
    assert talisman.force_https

    app = Flask(__name__)
    app.app_environment = "production"
    talisman = setup_talisman(app)
    assert talisman.force_https


def test_load_environment():
    app = Flask(__name__)
    load_environment(app)
    assert app.secret_key == os.getenv("APPSECRET", "secret")
    assert app.config["client_id"] == os.getenv("CLIENT_ID", None)
    assert app.config["cognito_domain"] == os.getenv("COGNITO_DOMAIN", None)
    assert app.config["client_secret"] == os.getenv("CLIENT_SECRET", None)
    assert app.config["redirect_host"] == os.getenv("REDIRECT_HOST")
    assert app.config["bucket_name"] == os.getenv("BUCKET_NAME")
    assert app.config["region"] == os.getenv("REGION")


def test_env_pool_id_development():
    user_pool_id = stubs.MOCK_COGNITO_USER_POOL_ID
    stubber = stubs.mock_cognito_list_pools()
    with stubber:
        assert env_pool_id() == user_pool_id


def test_env_pool_id_production(monkeypatch):
    user_pool_id = stubs.MOCK_COGNITO_USER_POOL_ID
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    stubber = stubs.mock_cognito_list_pools(env="prod")
    with stubber:
        assert env_pool_id() == user_pool_id


def test_list_pools():
    user_pool_id = stubs.MOCK_COGNITO_USER_POOL_ID
    stubber = stubs.mock_cognito_list_pools()

    with stubber:
        pools = list_pools()
        assert pools[0]["id"] == user_pool_id
        stubber.deactivate()


def test_get_cognito_pool_name():
    os.environ["APP_ENVIRONMENT"] = "production"
    assert get_cognito_pool_name() == "corona-cognito-pool-prod"
    os.environ["APP_ENVIRONMENT"] = "staging"
    assert get_cognito_pool_name() == "corona-cognito-pool-staging"
    os.environ["APP_ENVIRONMENT"] = "testing"
    assert get_cognito_pool_name() == "corona-cognito-pool-development"
