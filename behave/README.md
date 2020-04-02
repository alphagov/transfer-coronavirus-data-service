# End to end testing 

## Run locally 

`make run`

## Building the docker container 


```
# NOTE: Replace version with the bumped version number
docker build --no-cache -t gdscyber/concourse-chrome-driver -t gdscyber/concourse-chrome-driver:1.0 .

# Then to push to DockerHub:
docker push gdscyber/concourse-chrome-driver:1.0
docker push gdscyber/concourse-chrome-driver:latest 
```