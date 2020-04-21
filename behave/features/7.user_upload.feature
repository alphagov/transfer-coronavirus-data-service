# COVID19 - User upload files feature
Feature: COVID19 Data Transfer - User upload files
    Scenario: user can login
        Given credentials for the "standard-upload" group
        When you navigate to user home
        When you click on "#main-content .covid-transfer-signin-button"
        Then wait "5" seconds
        When oauth username is set
        When oauth password is set
        When oauth form is submitted
        Then wait "5" seconds
        Then the content of element with selector ".covid-transfer-page-title" contains "COVID-19 Data Transfer"
        Then the content of element with selector "#main-content .covid-transfer-username" contains username
        When I click on button "Upload"
        Then wait "5" seconds
        Then I fill in a filename
        When I click on button "Continue"
        Then I select a file to be uploaded
        When I click on button "Start upload"
        Then the content of element with selector "#upload_success" contains "Uploaded successfully."
