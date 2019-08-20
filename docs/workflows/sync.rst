.. _sync-workflow:

Synchronize a Repository
========================

Users can populate their repositories with content from an external source like Docker Hub by syncing
their repository.


Create a repository ``foo``
---------------------------

Start by creating a new repository named "foo"::

    $ http POST http://localhost:24817/pulp/api/v3/repositories/ name=foo

Response:

.. code::

    {
        "_href": "/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/",
        ...
    }

Save this url as an environment variable::

    $ export REPO_HREF=$(http :24817/pulp/api/v3/repositories/ | jq -r '.results[] | select(.name == "foo") | ._href')

Reference (pulpcore): `Repository API Usage
<https://docs.pulpproject.org/en/3.0/nightly/restapi.html#tag/repositories>`_


.. _create-remote:

Create a Remote
---------------

Creating a remote object informs Pulp about an external content source. In this case, we will be
using Docker Hub, but ``pulp-docker`` remotes can be anything that implements the registry API,
including `quay`, `google container registry`, or even another instance of Pulp.

Docker remotes can be configured with a ``policy``. The default value is ``immediate``. All
manifests and blobs are downloaded and saved during a sync with the ``immediate`` policy. When a
remote with an ``on_demand`` policy is used to sync a repository, only tags and manifests are
downloaded. Blobs are only downloaded when they are requested for the first time by a client.  The
``streamed`` policy does not ever save any blobs and simply streams them to the client with every
request. ``on_demand`` and ``streamed`` policies can provide significant disk space savings.

Create the remote by POST to the remotes endpoint::

    $ http POST http://localhost:24817/pulp/api/v3/remotes/docker/docker/ name='busybox' upstream_name='library/busybox' url='https://registry-1.docker.io' policy='on_demand'

.. code::

    {
        "_href": "/pulp/api/v3/remotes/docker/docker/f300a4a2-1348-4fce-9836-824203e5130e/",
        ...
    }

Save this url as an environment variable::

    $ export REMOTE_HREF=$(http :24817/pulp/api/v3/remotes/docker/docker/ | jq -r '.results[] | select(.name == "busybox") | ._href')


.. _filtered-sync-workflow:

.. note::
    Use `whitelist_tags` when only a subset of tags are needed to be synced from the remote source.


Reference: `Docker Remote Usage <../restapi.html#tag/remotes>`_

Sync repository ``foo`` using Remote ``bar``
----------------------------------------------

Use the remote object to kick off a synchronize task by specifying the repository to
sync with. You are telling pulp to fetch content from the remote and add to the repository::


    $ http POST ':24817'$REMOTE_HREF'sync/' repository=$REPO_HREF`` mirror=False

Response::

    {
        "task": "/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/"
    }

You can follow the progress of the task with a GET request to the task href. Notice that when the
synchronize task completes, it creates a new version, which is specified in ``created_resources``::

    $  http $BASE_ADDR/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/

Reference: `Docker sync Usage <../restapi.html#operation/remotes_docker_docker_sync>`_


.. _versioned-repo-created:

Look at the new Repository Version created
------------------------------------------

Every time content is added or removed from a repository, a new repository version is created::

    $ http GET ':24817'$REPO_HREF'versions/1/'

Response:

.. code:: json

    {
        "_created": "2019-08-07T20:46:11.311539Z",
        "_href": "/pulp/api/v3/repositories/84a3ea29-1444-43c6-92da-14da25f543ec/versions/1/",
        "base_version": null,
        "content_summary": {
            "added": {
                "docker.blob": {
                    "count": 487,
                    "href": "/pulp/api/v3/content/docker/blobs/?repository_version_added=/pulp/api/v3/repositories/84a3ea29-1444-43c6-92da-14da25f543ec/versions/1/"
                },
                "docker.manifest": {
                    "count": 307,
                    "href": "/pulp/api/v3/content/docker/manifests/?repository_version_added=/pulp/api/v3/repositories/84a3ea29-1444-43c6-92da-14da25f543ec/versions/1/"
                },
                "docker.tag": {
                    "count": 135,
                    "href": "/pulp/api/v3/content/docker/tags/?repository_version_added=/pulp/api/v3/repositories/84a3ea29-1444-43c6-92da-14da25f543ec/versions/1/"
                }
            },
            "present": {
                "docker.blob": {
                    "count": 487,
                    "href": "/pulp/api/v3/content/docker/blobs/?repository_version=/pulp/api/v3/repositories/84a3ea29-1444-43c6-92da-14da25f543ec/versions/1/"
                },
                "docker.manifest": {
                    "count": 307,
                    "href": "/pulp/api/v3/content/docker/manifests/?repository_version=/pulp/api/v3/repositories/84a3ea29-1444-43c6-92da-14da25f543ec/versions/1/"
                },
                "docker.tag": {
                    "count": 135,
                    "href": "/pulp/api/v3/content/docker/tags/?repository_version=/pulp/api/v3/repositories/84a3ea29-1444-43c6-92da-14da25f543ec/versions/1/"
                }
            },
            "removed": {}
        },
        "number": 1
    }

Reference (pulpcore): `Repository Version API Usage
<https://docs.pulpproject.org/en/3.0/nightly/restapi.html#operation/repositories_versions_read>`_
