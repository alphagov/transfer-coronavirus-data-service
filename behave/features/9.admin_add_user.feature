# COVID19 - Admin page feature
Feature: COVID19 Data Transfer - Admin add users
    @admin
    Scenario: Can add user
        Given credentials for the "admin-full" group
        When you login with these credentials
        Then you can go to the admin page
        When I click on button "New user"
        Then wait "5" seconds
        When you see the new user page
        Then you can see the options to allow the new user to download data
        When you select account type "standard-upload"
        Then you can see the options to allow the new user to download data
        When you select account type "admin-view"
        Then you cannot see options to allow the new user to download data
        When you select account type "admin-power"
        Then you cannot see options to allow the new user to download data
        When you select account type "admin-full"
        Then you cannot see options to allow the new user to download data

    @admin
    Scenario: Can see existing user
        Given credentials for the "admin-full" group
        When you login with these credentials
        When you enter the email address of an existing user
        When I click on button "Go to user"
        Then you see the manage user page


