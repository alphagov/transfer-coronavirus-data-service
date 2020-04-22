# COVID19 - Homepage Feature
Feature: COVID19 Data Transfer - Homepage loads
    @user
    Scenario: can load homepage
        When you navigate to user home
        Then the content of element with selector ".covid-transfer-page-title" contains "COVID-19 Data Transfer"
