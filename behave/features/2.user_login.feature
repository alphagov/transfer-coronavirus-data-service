# COVID19 - User login feature
Feature: COVID19 Data Transfer - User login
    @user
    Scenario: user can login
        Given credentials for the "standard-upload" group
        When you navigate to user home
        When you click on "#main-content .covid-transfer-signin-button"
        Then wait "5" seconds
        When oauth username is set
        When oauth password is set
        # When oauth sign in button is clicked
        When oauth form is submitted
        Then wait "5" seconds
        Then the content of element with selector ".covid-transfer-page-title" contains "COVID-19 Data Transfer"
        Then the content of element with selector "#main-content .covid-transfer-email" contains username
