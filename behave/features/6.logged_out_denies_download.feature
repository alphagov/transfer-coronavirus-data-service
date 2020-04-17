# COVID19 - Deny logged out access to download
Feature: COVID19 Data Transfer - Logged out download route is denied
    Scenario: cannot access download route when logged out
        When you navigate to "download/web-app-prod-data/other/gds/test.csv"
        Then you get redirected to route: "/403"