# transfer-coronavirus-data-service
Serve files from S3 based on a user database managed in Cognito.

## Cognito User Management

Provide access to data about vulnerable users to local authorities
for home support and to wholesalers for home delivery.

The data needs to be access controlled to ensure that we are not
exposing sensitive data to the wrong people.

The data is being broken down by local authority and sanitised into
S3 with appropriate data for the relevant consumers.

The access is controlled by a flask app running on PaaS using
AWS Cognito to authenticate users. We import lists of users
supplied by MHCLG into Cognito. Users are notified by email and
required to supply a 2FA code via SMS.

Once logged in, the app collects a set of objects from S3 which
match the prefixes supplied as a `;` delimited list in the
`custom:paths` attribute for their account.

The links are presigned URLs to S3 with a short expiration time.  

## S3 folder layout

- web-app-[env]-data
  - local_authority (only accessed if `is_la` is true)
    - blackpool
  - wholesaler
  - dwp

This configuration is handled via an ignored file called `s3paths.json`

GDS users can generate this file by running `make s3paths` 

## Admin interface
Using the admin interface:
```
cd app/
eval $(gds aws security-test -e); make admin_test
```
or
```
cd app/
eval $(gds aws govuk-corona-data-staging-cognito -e); make admin_staging
```
or
```
cd app/
eval $(gds aws govuk-corona-data-prod-cognito -e); make admin_prod
```

Open <http://localhost:8000>...


### Changing users access

`aws cognito-idp admin-update-user-attributes --user-pool-id eu-west-2_uXyAx3ObX --username ollie --user-attributes Name=custom:paths,Value='local_authority/london/bexley;local_authority/london/greenwich' Name=custom:is_la,Value=1 --region eu-west-2`

### Updating email

`aws cognito-idp admin-update-user-attributes --user-pool-id eu-west-2_AAA --username BBB --user-attributes Name=email,Value=CCC Name=email_verified,Value=true --region eu-west-2`

Where `AAA` is the rest of the user pool ID, `BBB` is the username and `CCC` is email address.

### Updating phone numbers:

`aws cognito-idp admin-update-user-attributes --user-pool-id eu-west-2_AAA --username BBB --user-attributes Name=phone_number,Value=CCC Name=phone_number_verified,Value=true --region eu-west-2`

Where `AAA` is the rest of the user pool ID, `BBB` is the username and `CCC` is phone number in `+441234567891` format.

### Resetting a user's password

This must be done by the user. Check their details, email and phone number in the [console](https://eu-west-2.console.aws.amazon.com/cognito/users/?region=eu-west-2#/pool/eu-west-2_pjM9bY9eD/users?_k=0ud4ot) or by running:

`aws cognito-idp list-users --user-pool-id eu-west-2_AAA --region eu-west-2 --filter "username = 'BBB'" | jq`

Where `AAA` is rest of the user pool and `BBB` is username.

At the bottom of the login is a "Forgot your password?" link. This will email the user a code.

[This is also the link.](https://cyber-manual-test-73hdxjhsy2jmap.auth.eu-west-2.amazoncognito.com/forgotPassword?client_id=2s4ccdrs0urfa4lih383m7tmk5&response_type=code&redirect_uri=https://temp-download-test.cloudapps.digital&scope=profile+email+phone+openid)


## How to run

To run the app locally you will need the following
parameters defined in
AWS Systems Manager > Parameter Store

```ssm
/transfer-coronavirus-data-service/cognito/client_id
/transfer-coronavirus-data-service/cognito/client_secret
/transfer-coronavirus-data-service/cognito/domain
/transfer-coronavirus-data-service/s3/bucket_name
```

### make run

Run a local python server running the flask app on port 8000

### make install

Install the dev and runtime requirements

### make checks

Run linters black, flake8 etc.

### make test

Run linters and then pytests

### make zip

Build the distributable zip file for shipping to PaaS


## End to end testing 

### Run locally

You need to export some local environment variables. You can add them
 to `behave_env.sh` (included in .gitignore). Contents should be like
the following: 

```behave_env.sh
export E2E_STAGING_ROOT_URL=https://localhost:8000/
export E2E_STAGING_USERNAME=[e2e_username_value]
export E2E_STAGING_PASSWORD=[e2e_password_value]
```  

The credentials should be for a cognito account which is 
able to login without an MFA SMS. 

Then (assuming you have the correct permissions) you can run

```
source behave_env.sh
eval $(gds aws security-test -e); make e2e
```

### Running against staging 

The tests are automatically run against staging in the 
pipeline but can be run manually by assuming a 
different role and setting different credentials. 

## Configuration

The config.py module provides an interface to the  
standard Flask app.config. The interface makes it 
easier and more effective to set and get 
configuration values. We retrieve configuration 
settings without having to import the app every 
time by using config functions in modules which 
don't have access to the flask app object.

A number of settings are passed into the app as 
environment variables and these are loaded into 
app.config as the first step of the local run module 
and the lambda lambda_handler module.

## Docker base image

The build for the `gdscyber/concourse-chrome-driver`
base image used to live here but has been transfered 
to the Cyber Security team. 

For questions about the base image please ask in 
#cyber-security-help or email 
[cyber.security@digital.cabinet-office.gov.uk](mailto:cyber.security@digital.cabinet-office.gov.uk) 


   