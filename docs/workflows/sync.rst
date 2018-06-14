Synchronize a Repository
========================

Users can populate their repositories with content from an external source like Docker Hub by
syncing their repository.

Create a Repository
-------------------

Start by creating a new repository named "bar"::

    $ http POST $BASE_ADDR/pulp/api/v3/repositories/ name=bar

Response::

    {
        "_href": "http://localhost:8000/pulp/api/v3/repositories/e81221c3-9c7a-4681-a435-aa74020753f2/",
        ...
    }

If you want to copy/paste your way through the guide, create an environment variable for the repository URI::

    $ export REPO_HREF=$(http $BASE_ADDR/pulp/api/v3/repositories/ | jq -r '.results[] | select(.name == "bar") | ._href')


Create a Remote
---------------

Creating a remote object informs Pulp about an external content source.

You can use any Docker remote to sync content into any repository::

    $ http POST $BASE_ADDR/pulp/api/v3/remotes/docker/ \
        name='bar' \
        url='https://updateme.example.com'

Response::

    {
        "_href": "http://localhost:8000/pulp/api/v3/repositories/bar/remotes/docker/3750748b-781f-48df-9734-df014b2a11b4/",
        ...
    }

Again, you can create an environment variable for convenience::

    $ export REMOTE_HREF=$(http $BASE_ADDR/pulp/api/v3/remotes/docker/ | jq -r '.results[] | select(.name == "bar") | ._href')

Sync repository bar with remote
-------------------------------

Use the remote object to kick off a synchronize task by specifying the repository to
sync with. You are telling pulp to fetch content from the remote and add to the repository::

    $ http POST $REMOTE_HREF'sync/' repository=$REPO_HREF

Response::

    {
        "_href": "http://localhost:8000/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/",
        "task_id": "3896447a-2799-4818-a3e5-df8552aeb903"
    }

You can follow the progress of the task with a GET request to the task href. Notice that when the
synchroinze task completes, it creates a new version, which is specified in ``created_resources``::

    $  http $BASE_ADDR/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/

Response::

    {
        "_href": "http://localhost:8000/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/",
        "created": "2018-05-01T17:17:46.558997Z",
        "created_resources": [
            "http://localhost:8000/pulp/api/v3/repositories/593e2fa9-af64-4d4b-aa7b-7078c96f2443/versions/6/"
        ],
        "error": null,
        "finished_at": "2018-05-01T17:17:47.149123Z",
        "non_fatal_errors": [],
        "parent": null,
        "progress_reports": [
            {
                "done": 0,
                "message": "Add Content",
                "state": "completed",
                "suffix": "",
                "task": "http://localhost:8000/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/",
                "total": 0
            },
            {
                "done": 0,
                "message": "Remove Content",
                "state": "completed",
                "suffix": "",
                "task": "http://localhost:8000/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/",
                "total": 0
            }
        ],
        "spawned_tasks": [],
        "started_at": "2018-05-01T17:17:46.644801Z",
        "state": "completed",
        "worker": "http://localhost:8000/pulp/api/v3/workers/eaffe1be-111a-421d-a127-0b8fa7077cf7/"
    }
