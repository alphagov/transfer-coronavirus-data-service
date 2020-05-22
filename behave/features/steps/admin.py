import os

import user_routes
from behave import then, when
from selenium.webdriver.support.select import Select


@then("you can go to the admin page")
def can_go_to_admin_page(context):
    url = os.environ["E2E_STAGING_ROOT_URL"]
    url += "admin"
    context.browser.get(url)
    assert context.browser.current_url == url
    context.execute_steps(
        """
        Then the content of element with selector"""
        + """ ".covid-transfer-page-title" contains "COVID-19 Data Transfer" """
        + """
        Then the content of element with selector"""
        + """ "#main-content .covid-transfer-username" contains username"""
        + """
        Then the content of element with selector"""
        + """ "#main-content .govuk-heading-l" contains "User administration"
    """
    )


@then("you cannot go to the admin page and are redirected")
def cannot_go_to_admin_page_and_are_redirected(context):
    base_url = os.environ["E2E_STAGING_ROOT_URL"]
    admin_url = f"{base_url}admin"
    context.browser.get(admin_url)
    assert context.browser.current_url == base_url + "403"
    context.execute_steps(
        """
        Then the content of element with selector"""
        + """ ".govuk-error-summary__list" contains "User not authorised to access this route"
    """
    )


@when("you see the new user page")
def see_new_user_page(context):
    context.execute_steps(
        """
    Then the content of element with selector ".govuk-heading-l" contains "Edit user"
    """
    )


@then("you can see the options to allow the new user to download data")
def see_options_to_allow_new_user_to_download_data(context):
    assert context.browser.find_element_by_id("standard-user-inputs").is_displayed()


@then("you cannot see options to allow the new user to download data")
def cannot_see_options_to_allow_new_user_to_download_data(context):
    assert not context.browser.find_element_by_id("standard-user-inputs").is_displayed()


@when('you select account type "{type}"')
def select_account_type(context, type):
    account_select = Select(context.browser.find_element_by_id("account-select"))
    account_select.select_by_value(type)


@when("you enter the email address of an existing user")
def edit_existing_user(context):
    elem = context.browser.find_element_by_id("input-email")
    elem.send_keys(user_routes.username_for_group_name("standard-download"))


@then("you see the manage user page")
def see_manage_user_page(context):
    username = user_routes.username_for_group_name("standard-download")
    context.execute_steps(
        f"""
    Then the content of element with selector ".govuk-heading-l" contains "Manage user"
    Then the content of element with selector "#user_email" contains "{username}"
    """
    )
    assert context.browser.find_element_by_xpath(
        "//*[contains(@class, 'govuk-button')][text()[contains(., 'Reinvite')]]"
    )
    assert context.browser.find_element_by_xpath(
        "//*[contains(@class, 'govuk-button')][text()[contains(., 'Disable')]]"
    )
    assert context.browser.find_element_by_xpath(
        "//*[contains(@class, 'govuk-button')][text()[contains(., 'Delete')]]"
    )
