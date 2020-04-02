# COVID19 - User login feature
Feature: COVID19 Data Transfer - User login
    Scenario: user can login
        Given the credentials
        When you navigate to user home
        When you click on ".govuk-button"
        Then wait "5" seconds
        When oauth username is set
        When oauth password is set
        # When oauth sign in button is clicked
        When oauth form is submitted
        Then wait "5" seconds
        Then the content of element with selector ".govuk-heading-xl" contains "COVID-19 Data Transfer"
        Then the content of element with selector "#main-content :nth-child(2)" contains username