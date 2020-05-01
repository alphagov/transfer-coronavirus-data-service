# COVID19 - Admin page feature
Feature: COVID19 Data Transfer - Admin page
    @admin
    Scenario: Logged in as an admin-view user
        Given credentials for the "admin-view" group
        When you login with these credentials
        Then you can go to the admin page

    @admin
    Scenario: Logged in as an admin-power user
        Given credentials for the "admin-power" group
        When you login with these credentials
        Then you can go to the admin page
        Then the button "Go to user" does exist
        Then the button "New user" does not exist

    @admin
    Scenario: Logged in as an admin-full user
        Given credentials for the "admin-full" group
        When you login with these credentials
        Then you can go to the admin page

    @admin
    Scenario: Logged in as a standard-download user
        Given credentials for the "standard-download" group
        When you login with these credentials
        Then you cannot go to the admin page and are redirected

    @admin
    Scenario: Logged in as a standard-upload user
        Given credentials for the "standard-upload" group
        When you login with these credentials
        Then you cannot go to the admin page and are redirected
