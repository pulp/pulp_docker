#!/usr/bin/env bash
echo "Creating a remote that points to an external source of container images."
http POST $BASE_ADDR/pulp/api/v3/remotes/docker/docker/ \
    name='my-hello-repo' \
    url='https://registry-1.docker.io' \
    upstream_name='pulp/test-fixture-1'

echo "Export an environment variable for the new remote URI."
export REMOTE_HREF=$(http $BASE_ADDR/pulp/api/v3/remotes/docker/docker/ \
    | jq -r '.results[] | select(.name == "my-hello-repo") | ._href')

echo "Inspecting new Remote."
http $BASE_ADDR$REMOTE_HREF
