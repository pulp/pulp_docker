Upload and Manage Content
=========================
# TODO(asmacdo) check for pulp_python

Create a repository
-------------------

If you don't already have a repository, create one::

    $ http POST $BASE_ADDR/pulp/api/v3/repositories/ name=bar

Response::

    {
        "_href": "http://localhost:8000/pulp/api/v3/repositories/e81221c3-9c7a-4681-a435-aa74020753f2/",
        ...
    }

Create a variable for convenience::

    $ export REPO_HREF=$(http $BASE_ADDR/pulp/api/v3/repositories/ | jq -r '.results[] | select(.name == "bar") | ._href')


Upload a file to Pulp
---------------------

Each artifact in Pulp represents a file. They can be created during sync or created manually by uploading a file::

    $ export ARTIFACT_HREF=$(http --form POST $BASE_ADDR/pulp/api/v3/artifacts/ file@./myfilename | jq -r '._href')

Response::

    {
        "_href": "http://localhost:8000/pulp/api/v3/artifacts/7d39e3f6-535a-4b6e-81e9-c83aa56aa19e/",
        ...
    }


Create content from an artifact
-------------------------------

Stub

Add content to a repository
---------------------------

Stub
