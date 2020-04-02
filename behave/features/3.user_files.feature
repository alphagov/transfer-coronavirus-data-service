# COVID19 - User access files feature
Feature: COVID19 Data Transfer - User files
    Scenario: user can login
        Given the credentials
        When you navigate to user home
        When you click on "#main-content .govuk-button--start"
        Then wait "5" seconds
        Then the content of element with selector ".govuk-heading-xl" contains "COVID-19 Data Transfer"
        Then the content of element with selector "#main-content :nth-child(2)" contains username
        Then the content of element with selector "#main-content a[href^='/download']" equals "web-app-prod-data/other/gds/not-real-data-other-gds.csv"