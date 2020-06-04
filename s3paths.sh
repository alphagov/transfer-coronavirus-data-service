#!/bin/bash

curdir=$(pwd)
cd ../covid-engineering/reliability-engineering/terraform/modules/coronavirus-transfer-service-s3-config/local
terraform init
terraform plan
pwd
cp s3paths.json $curdir
cd $curdir