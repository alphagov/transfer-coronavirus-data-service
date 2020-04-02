import time

from behave import then, when


@when('visit url "{url}"')
def visit_url_step(context, url):
    context.browser.get(url)


@when('you click on "{selector}"')
def click_on_step(context, selector):
    elem = context.browser.find_element_by_css_selector(selector)
    elem.click()
    time.sleep(5)


@when('field with name "{selector}" is given "{value}"')
def set_field_value_step(context, selector, value):
    elem = context.browser.find_element_by_name(selector)
    elem.send_keys(value)
    elem.submit()
    time.sleep(5)


@then('title becomes "{title}"')
def check_browser_title_step(context, title):
    assert context.browser.title == title
