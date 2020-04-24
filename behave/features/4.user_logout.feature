# COVID19 - User access to files
Feature: COVID19 Data Transfer - User files
    @user
    Scenario: user can logout
        Given credentials for the "standard-upload" group
        When you login with these credentials
        When you navigate to user home
        When you click on "#main-content .covid-transfer-logout-button"
        Then wait "5" seconds
        Then the content of element with selector ".covid-transfer-page-title" contains "COVID-19 Data Transfer"
        Then the content of element with selector "#main-content .covid-transfer--welcome-text" equals "This is a new service for pre-registered users to access."
