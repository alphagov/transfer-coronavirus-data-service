# COVID19 - Deny logged out access to files
Feature: COVID19 Data Transfer - Logged out files route is denied
    @user
    Scenario: cannot access files route when logged out
        When you navigate to "files"
        Then you get redirected to route: "/403"
