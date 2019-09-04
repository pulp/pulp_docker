#!/bin/bash

# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by bootstrap.py. Please use
# bootstrap.py to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

set -euv

echo "---
:rubygems_api_key: $RUBYGEMS_API_KEY" > ~/.gem/credentials
sudo chmod 600 ~/.gem/credentials

django-admin runserver 24817 >> ~/django_runserver.log 2>&1 &
sleep 5

cd $TRAVIS_BUILD_DIR
export REPORTED_VERSION=$(http :24817/pulp/api/v3/status/ | jq --arg plugin pulp_docker -r '.versions[] | select(.component == $plugin) | .version')
export DESCRIPTION="$(git describe --all --exact-match `git rev-parse HEAD`)"
if [[ $DESCRIPTION == 'tags/'$REPORTED_VERSION ]]; then
  export VERSION=${REPORTED_VERSION}
else
  export EPOCH="$(date +%s)"
  export VERSION=${REPORTED_VERSION}${EPOCH}
fi

export response=$(curl --write-out %{http_code} --silent --output /dev/null https://rubygems.org/gems/pulp_docker_client/versions/$VERSION)

if [ "$response" == "200" ];
then
    exit
fi

cd
git clone https://github.com/pulp/pulp-openapi-generator.git
cd pulp-openapi-generator

./generate.sh pulp_docker ruby $VERSION
cd pulp_docker-client
gem build pulp_docker_client
GEM_FILE="$(ls | grep pulp_docker_client-)"
gem push ${GEM_FILE}
