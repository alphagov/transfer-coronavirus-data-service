import os

from behave import then


@then("I fill in a filename")
def fill_in_filename(context):
    elem = context.browser.find_element_by_id("file_name")
    elem.click()
    elem.send_keys("my_filename")


@then("I select a file to be uploaded")
def select_file_to_be_uploaded(context):
    elem = context.browser.find_element_by_id("file")
    elem.send_keys(f"{os.getcwd()}/features/fixtures/file_to_upload.csv")
