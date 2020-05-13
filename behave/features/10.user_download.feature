# COVID19 - User download files feature
Feature: COVID19 Data Transfer - User download files
    @user
    Scenario: user can download files
        Given credentials for the "standard-download" group
        When you login with these credentials
        When I click on button "Downloads"
        Then wait "5" seconds
        Then you download link from ".covid-transfer-download-section .covid-tranfer-file-link:first-of-type"
