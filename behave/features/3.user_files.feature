# COVID19 - User access files feature
Feature: COVID19 Data Transfer - User files
    @user
    Scenario: user can see files for download
        Given credentials for the "standard-upload" group
        When you login with these credentials
        When you navigate to user home
        When you click on "#main-content .covid-transfer-files-button"
        Then wait "5" seconds
        Then the content of element with selector ".covid-transfer-page-title" contains "COVID-19 Data Transfer"
        Then the content of element with selector "#main-content .covid-transfer-email" contains username
        Then the link with css selector "#main-content .covid-transfer-download-section a.covid-tranfer-file-link" and text "other/gds/not-real-data-other-gds.csv" does exist