# COVID19 - Homepage Feature
Feature: COVID19 Data Transfer - Homepage loads
    Scenario: can load homepage
        When you navigate to user home
        Then the content of element with selector ".govuk-heading-xl" contains "COVID-19 Data Transfer"
