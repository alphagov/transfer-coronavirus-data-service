# End to end testing 

## Run locally

You need a `behave_env.sh` file which should look like 
the following: 

```behave_env.sh
#! /bin/bash
export E2E_STAGING_ROOT_URL=https://corona-backend-consumer-stag.cloudapps.digital/
export E2E_STAGING_USERNAME=[e2e_username_value]
export E2E_STAGING_PASSWORD=[e2e_password_value]
```  

The credentials need to be for a cognito account which is 
able to login without an MFA SMS. 

Then you can run

`make run`

## Building the docker container 


```
# NOTE: Replace version with the bumped version number
docker build --no-cache -t gdscyber/concourse-chrome-driver -t gdscyber/concourse-chrome-driver:1.0 .

# Then to push to DockerHub:
docker push gdscyber/concourse-chrome-driver:1.0
docker push gdscyber/concourse-chrome-driver:latest 
```