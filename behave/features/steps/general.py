import time

from behave import then, when
from selenium.common.exceptions import NoSuchElementException


@when('visit url "{url}"')
def visit_url_step(context, url):
    context.browser.get(url)


@when('you click on "{selector}"')
def click_on_step(context, selector):
    elem = context.browser.find_element_by_css_selector(selector)
    elem.click()
    time.sleep(5)


@when('I click on button "{text}"')
def click_on_button(context, text):
    elem = context.browser.find_element_by_xpath(
        "//*[contains(@class, 'govuk-button')][text()[contains(., '{}')]]".format(text)
    )
    elem.click()
    time.sleep(5)


@then('the button "{text}" does exist')
def button_is_there(context, text):
    try:
        context.browser.find_element_by_xpath(
            "//*[contains(@class, 'govuk-button')][text()[contains(., '{}')]]".format(
                text
            )
        )
        element_found = True
    except NoSuchElementException:
        element_found = False

    assert element_found


@then('the button "{text}" does not exist')
def button_is_not_there(context, text):
    try:
        context.browser.find_element_by_xpath(
            "//*[contains(@class, 'govuk-button')][text()[contains(., '{}')]]".format(
                text
            )
        )
        element_found = True
    except NoSuchElementException:
        element_found = False

    assert not element_found


@when('field with name "{selector}" is given "{value}"')
def set_field_value_step(context, selector, value):
    elem = context.browser.find_element_by_name(selector)
    elem.send_keys(value)
    elem.submit()
    time.sleep(5)


@then('title becomes "{title}"')
def check_browser_title_step(context, title):
    assert context.browser.title == title


@then('wait "{seconds}" seconds')
def wait_step(context, seconds):
    time.sleep(int(seconds))
