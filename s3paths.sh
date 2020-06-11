#!/bin/bash

if [[ -d "../covid-engineering" ]]; then
  curdir=$(pwd)
  cd ../covid-engineering/reliability-engineering/terraform/modules/coronavirus-transfer-service-s3-config/local
  terraform init
  terraform plan
  terraform apply -auto-approve
  cp s3paths.json $curdir
  cd $curdir
else
  echo "You need to checkout the alphagov/covid-engineering repository."
  echo "Users without access can generate a file that matches: s3paths.example.json"
fi