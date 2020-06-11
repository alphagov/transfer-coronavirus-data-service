# COVID19 - User can see their upload file history
Feature: COVID19 Data Transfer - User upload file history
    @user
    Scenario: user can see upload file history
        Given credentials for the "standard-upload" group
        When you login with these credentials
        When I click on button "Upload"
        Then wait "5" seconds
        Then the content of element with selector ".covid-transfer-page-title" contains "COVID-19 Data Transfer"
        Then the content of element with selector "#main-content .covid-transfer-username" contains username
        Then the content of element with selector "#main-content .covid-transfer-upload-section" contains "other/gds/MOCK_DATA.csv"

