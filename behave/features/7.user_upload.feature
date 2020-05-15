# COVID19 - User upload files feature
Feature: COVID19 Data Transfer - User upload files
    @user
    Scenario: user can upload files
        Given credentials for the "standard-upload" group
        When you login with these credentials
        When I click on button "Upload"
        Then wait "5" seconds
        Then I fill in a filename
        When I click on button "Continue"
        Then I select a file to be uploaded
        When I click on button "Start upload"
        Then wait "5" seconds
        Then an element with selector "#upload_success" does exist
        Then an element with selector "#upload_success.hidden" does not exist
        Then the content of element with selector "#upload_success" contains "Uploaded successfully."

