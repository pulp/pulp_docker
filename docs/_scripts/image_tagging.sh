#!/usr/bin/env bash

export TAG_NAME='custom_tag'
export MANIFEST_DIGEST='sha256:b8ba256769a0ac28dd126d584e0a2011cd2877f3f76e093a7ae560f2a5301c00'

echo "Tagging the manifest."
export TASK_URL=$(http POST $BASE_ADDR'/pulp/api/v3/docker/tag/' \
  repository=$REPO_HREF tag=$TAG_NAME digest=$MANIFEST_DIGEST \
  | jq -r '.task')

wait_until_task_finished $BASE_ADDR$TASK_URL

echo "Getting a reference to a newly created tag."
export CREATED_TAG=$(http $BASE_ADDR$TASK_URL \
  | jq -r '.created_resources | .[] | select(test("content"))')

echo "Display properties of the created tag."
http $BASE_ADDR$CREATED_TAG
