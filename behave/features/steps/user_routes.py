import os
import time

from behave import given, then, when


@given("the credentials")
def credentials_step(context):
    context.browser.header_overrides = {
        "e2e_username": os.environ["E2E_STAGING_USERNAME"],
        "e2e_password": os.environ["E2E_STAGING_PASSWORD"],
    }


@when("oauth username is set")
def login_username_step(context):
    elem = context.browser.find_element_by_css_selector(
        ".visible-md .modal-body #signInFormUsername"
    )
    elem.click()
    elem.send_keys(context.browser.header_overrides["e2e_username"])


@when("oauth password is set")
def login_password_step(context):
    elem = context.browser.find_element_by_css_selector(
        ".visible-md .modal-body #signInFormPassword"
    )
    elem.click()
    elem.send_keys(context.browser.header_overrides["e2e_password"])


@when("oauth form is submitted")
def login_submit_step(context):
    elem = context.browser.find_element_by_css_selector(
        ".visible-md .modal-body #signInFormPassword"
    )
    elem.submit()


@when("oauth sign in button is clicked")
def login_submit_button_click_step(context):
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
def user_redirect_step(context):
    url = os.environ["E2E_STAGING_ROOT_URL"]
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
