Publish and Host
================
# TODO(asmacdo) check for pulp_python

This section assumes that you have a repository with content in it. To do this, see the
:doc:`sync` or :doc:`upload` documentation.

Create a Publisher
------------------

Publishers contain extra settings for how to publish. You can use a Docker publisher on any
repository that contains Docker content::

$ http POST $BASE_ADDR/pulp/api/v3/publishers/docker/ name=bar

Response::

    {
        "_href": "http://localhost:8000/pulp/api/v3/repositories/bar/publishers/docker/bar/",
        ...
    }

Create a variable for convenience.::

$ export PUBLISHER_HREF=$(http $BASE_ADDR/pulp/api/v3/publishers/docker/ | jq -r '.results[] | select(.name == "bar") | ._href')


Publish a repository with a publisher
-------------------------------------

Use the publisher object to kick off a publish task by specifying the repository version to publish.
Alternatively, you can specify repository, which will publish the latest version::

$ http POST $PUBLISHER_HREF'publish/' repository=$REPO_HREF

Response::

    [
        {
            "_href": "http://localhost:8000/pulp/api/v3/tasks/fd4cbecd-6c6a-4197-9cbe-4e45b0516309/",
            "task_id": "fd4cbecd-6c6a-4197-9cbe-4e45b0516309"
        }
    ]

Create a variable for convenience.::

$ export PUBLICATION_HREF=$(http $BASE_ADDR/pulp/api/v3/publications/ | jq -r --arg PUBLISHER_HREF "$PUBLISHER_HREF" '.results[] | select(.publisher==$PUBLISHER_HREF) | ._href')

Host a Publication (Create a Distribution)
--------------------------------------------

To host a publication, users create a distribution which will serve the associated publication at
``/pulp/content/<distribution.base_path>`` as demonstrated in :ref:`using
distributions<using-distributions>`::

$ http POST $BASE_ADDR/pulp/api/v3/distributions/ name='baz' base_path='bar' publication=$PUBLICATION_HREF

Response::

    {
        "_href": "http://localhost:8000/pulp/api/v3/distributions/9b29f1b2-6726-40a2-988a-273d3f009a41/",
       ...
    }

.. _using-distributions:
