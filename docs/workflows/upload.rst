Upload and Manage Content
=========================

Create a repository
-------------------

If you don't already have a repository, create one::

    $ http POST $BASE_ADDR/pulp/api/v3/repositories/ name=foo

Response::

    {
        "_href": "http://localhost:24817/pulp/api/v3/repositories/1/",
        ...
    }

Reference (pulpcore): `Repository API Usage
<https://docs.pulpproject.org/en/3.0/nightly/restapi.html#tag/repositories>`_


Upload a file to Pulp
---------------------

Each artifact in Pulp represents a file. They can be created during sync or created manually by uploading a file::

    $ http --form POST $BASE_ADDR/pulp/api/v3/artifacts/ file@./my_content

Response::

    {
        "_href": "http://localhost:24817/pulp/api/v3/artifacts/1/",
        ...
    }

Reference (pulpcore): `Artifact API Usage
<https://docs.pulpproject.org/en/3.0/nightly/restapi.html#tag/artifacts>`_

Create content from an artifact
-------------------------------

.. warning::

    This section is currently not functional

Now that Pulp has the content, its time to make it into a unit of content.

    $ http POST $BASE_ADDR/pulp/api/v3/content/docker/ artifact=http://localhost:24817/pulp/api/v3/artifacts/1/ filename=my_content

Response::

    {
        "_href": "http://localhost:24817/pulp/api/v3/content/docker/1/",
        "_artifact": "http://localhost:24817/pulp/api/v3/artifacts/1/",
        "digest": "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c",
        "filename": "my-content",
    }

Reference: `Docker Content API Usage <../restapi.html#tag/content>`_

Add content to a repository
---------------------------

Once there is a content unit, it can be added and removed and from to repositories::

$ http POST $REPO_HREF/pulp/api/v3/repositories/1/versions/ add_content_units:="[\"http://localhost:24817/pulp/api/v3/content/docker/1/\"]"

This is entirely implemented by `pulpcore`, please see their reference docs for more information.

Reference (pulpcore): `Repository Version Creation API Usage
<https://docs.pulpproject.org/en/3.0/nightly/restapi.html#operation/repositories_versions_create>`_
