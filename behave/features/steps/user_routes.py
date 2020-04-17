import os
import re
import time

from behave import given, then, when


def get_plus_string(group_name):
    # To keep things short I've truncated the stage name
    # in the plus string from the CF_SPACE env var
    stages = {"testing": "test", "staging": "stage"}
    env = stages[os.environ.get("CF_SPACE", "testing")]

    # for a stupid reason I created all the test users
    # with a slightly different naming convention
    groups = {
        "standard-download": "user-download",
        "standard-upload": "user-upload",
    }
    if group_name in groups:
        group_suffix = groups[group_name]
    else:
        group_suffix = group_name

    plus_string = f"+c19-{env}-{group_suffix}"
    return plus_string


@given("the credentials")
def credentials_step(context):
    context.browser.header_overrides = {
        "e2e_username": os.environ["E2E_STAGING_USERNAME"],
        "e2e_password": os.environ["E2E_STAGING_PASSWORD"],
    }


@given('credentials for the "{group_name}" group')
def group_credentials_step(context, group_name):
    plus_string = get_plus_string(group_name)
    root_email = os.environ["E2E_STAGING_USERNAME"]
    e2e_username = root_email.replace("@", f"{plus_string}@")
    context.browser.header_overrides = {
        "e2e_username": e2e_username,
        "e2e_password": os.environ["E2E_STAGING_PASSWORD"],
    }


@when("oauth username is set")
def login_username_step(context):
    """
    The cognito signin form is rendered in HTML twice for difference screen sizes.
    The small screen version appears first in the HTML but is hidden by CSS.
    Without the .visible-md class this resolves the hidden form element and
    is unable to interact with the form.
    """
    elem = context.browser.find_element_by_css_selector(
        ".visible-md .modal-body #signInFormUsername"
    )
    elem.click()
    elem.send_keys(context.browser.header_overrides["e2e_username"])


@when("oauth password is set")
def login_password_step(context):
    """
    The cognito signin form is rendered in HTML twice for difference screen sizes.
    The small screen version appears first in the HTML but is hidden by CSS.
    Without the .visible-md class this resolves the hidden form element and
    is unable to interact with the form.
    """
    elem = context.browser.find_element_by_css_selector(
        ".visible-md .modal-body #signInFormPassword"
    )
    elem.click()
    elem.send_keys(context.browser.header_overrides["e2e_password"])


@when("oauth form is submitted")
def login_submit_step(context):
    """
    The cognito signin form is rendered in HTML twice for difference screen sizes.
    The small screen version appears first in the HTML but is hidden by CSS.
    Without the .visible-md class this resolves the hidden form element and
    is unable to interact with the form.
    """
    elem = context.browser.find_element_by_css_selector(
        ".visible-md .modal-body #signInFormPassword"
    )
    elem.submit()


@when("oauth sign in button is clicked")
def login_submit_button_click_step(context):
    """
    The cognito signin form is rendered in HTML twice for difference screen sizes.
    The small screen version appears first in the HTML but is hidden by CSS.
    Without the .visible-md class this resolves the hidden form element and
    is unable to interact with the form.
    """
    elem = context.browser.find_element_by_name(
        ".visible-md .modal-body .btn.btn-primary.submitButton-customizable"
    )
    elem.submit()


@when("you navigate to user home")
def user_home_step(context):
    url = os.environ["E2E_STAGING_ROOT_URL"]
    context.browser.get(url)


@when('you navigate to "{path}"')
def user_path_step(context, path):
    url = os.environ["E2E_STAGING_ROOT_URL"]
    context.browser.get(f"{url}{path}")


@then("you get redirected to user home")
def user_redirect_home_step(context):
    url = os.environ["E2E_STAGING_ROOT_URL"]
    assert context.browser.current_url == url


@then('you get redirected to route: "{route}"')
def user_redirect_to_route_step(context, route):
    url = re.sub("/$", route, os.environ["E2E_STAGING_ROOT_URL"])
    print(url)
    assert context.browser.current_url == url


@then('the content of element with selector "{selector}" equals "{title}"')
def content_equals_step(context, selector, title):
    elem = context.browser.find_element_by_css_selector(selector).text
    assert elem == title


@then('the content of element with selector "{selector}" contains "{part}"')
def content_contains_step(context, selector, part):
    elem = context.browser.find_element_by_css_selector(selector).text
    assert part in elem


@then('the content of element with selector "{selector}" contains username')
def content_contains_username_step(context, selector):
    elem = context.browser.find_element_by_css_selector(selector).text
    part = context.browser.header_overrides["e2e_username"]
    assert part in elem


@then('wait "{seconds}" seconds')
def wait_step(context, seconds):
    time.sleep(int(seconds))


@then("we have a session cookie")
def session_cookie_step(context):
    cookie = context.browser.get_cookie("session")
    assert cookie is not None
