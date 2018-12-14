``pulp_docker`` Plugin
===============================

This is the ``pulp_docker`` Plugin for `Pulp Project
3.0+ <https://pypi.python.org/pypi/pulpcore/>`__. This plugin provides Pulp with support for docker
images, similar to the ``pulp_docker`` plugin for Pulp 2.

All REST API examples below use `httpie <https://httpie.org/doc>`__ to
perform the requests.

.. code-block::

    machine localhost
    login admin
    password admin

If you configured the ``admin`` user with a different password, adjust the configuration
accordingly. If you prefer to specify the username and password with each request, please see
``httpie`` documentation on how to do that.

This documentation makes use of the `jq library <https://stedolan.github.io/jq/>`_
to parse the json received from requests, in order to get the unique urls generated
when objects are created. To follow this documentation as-is please install the jq
library with:

``$ sudo dnf install jq``

Install ``pulpcore``
--------------------

Follow the `installation
instructions <docs.pulpproject.org/en/3.0/nightly/installation/instructions.html>`__
provided with pulpcore.

Install plugin
--------------

This document assumes that you have
`installed pulpcore <https://docs.pulpproject.org/en/3.0/nightly/installation/instructions.html>`_
into a the virtual environment ``pulpvenv``.

Users should install from **either** PyPI or source.


Install ``pulp_docker`` from source
--------------------------------------------

.. code-block:: bash

   sudo -u pulp -i
   source ~/pulpvenv/bin/activate
   cd pulp_docker
   pip install -e .
   django-admin runserver


Install ``pulp_docker`` From PyPI
------------------------------------------

.. code-block:: bash

   sudo -u pulp -i
   source ~/pulpvenv/bin/activate
   pip install pulp-docker
   django-admin runserver


Make and Run Migrations
-----------------------

.. code-block:: bash

   pulp-manager makemigrations pulp_docker
   pulp-manager migrate pulp_docker

Run Services
------------

.. code-block:: bash

   pulp-manager runserver
   gunicorn pulpcore.content:server --bind 'localhost:8080' --worker-class 'aiohttp.GunicornWebWorker' -w 2
   sudo systemctl restart pulp_resource_manager
   sudo systemctl restart pulp_worker@1
   sudo systemctl restart pulp_worker@2


Create a repository ``foo``
---------------------------

``$ http POST http://localhost:8000/pulp/api/v3/repositories/ name=foo``

.. code:: json

    {
        "_href": "/pulp/api/v3/repositories/1/",
        ...
    }

``$ export REPO_HREF=$(http :8000/pulp/api/v3/repositories/ | jq -r '.results[] | select(.name == "foo") | ._href')``

Create a new remote ``bar``
---------------------------

``$ http POST http://localhost:8000/pulp/api/v3/remotes/docker/ name='dockerhub/busybox' upstream_name='busybox' url='https://registry-1.docker.io'``

.. code:: json

    {
        "_href": "/pulp/api/v3/remotes/docker/1/",
        ...
    }

``$ export REMOTE_HREF=$(http :8000/pulp/api/v3/remotes/docker/ | jq -r '.results[] | select(.name == "dockerhub/busybox") | ._href')``


Sync repository ``foo`` using Remote ``bar``
----------------------------------------------

``$ http POST ':8000'$REMOTE_HREF'sync/' repository=$REPO_HREF``

Look at the new Repository Version created
------------------------------------------

``$ http GET ':8000'$REPO_HREF'versions/1/'``

.. code:: json

    {
        "_added_href": "/pulp/api/v3/repositories/1/versions/1/added_content/",
        "_content_href": "/pulp/api/v3/repositories/1/versions/1/content/",
        "_href": "/pulp/api/v3/repositories/1/versions/1/",
        "_removed_href": "/pulp/api/v3/repositories/1/versions/1/removed_content/",
        "content_summary": {
            "docker": 3
        },
        "created": "2018-02-23T20:29:54.499055Z",
        "number": 1
    }

Create a ``docker`` Publisher ``baz``
----------------------------------------------

``$ http POST http://localhost:8000/pulp/api/v3/publishers/docker/ name=baz``

.. code:: json

    {
        "_href": "/pulp/api/v3/publishers/docker/1/",
        ...
    }

``$ export PUBLISHER_HREF=$(http :8000/pulp/api/v3/publishers/docker/ | jq -r '.results[] | select(.name == "baz") | ._href')``


Use the ``bar`` Publisher to create a Publication
-------------------------------------------------

``$ http POST ':8000'$PUBLISHER_HREF'publish/' repository=$REPO_HREF``

.. code:: json

    {
        "task": "/pulp/api/v3/tasks/fd4cbecd-6c6a-4197-9cbe-4e45b0516309/"
    }

``$ export PUBLICATION_HREF=$(http :8000/pulp/api/v3/publications/ | jq -r --arg PUBLISHER_HREF "$PUBLISHER_HREF" '.results[] | select(.publisher==$PUBLISHER_HREF) | ._href')``

Add a Docker Distribution to serve your publication
---------------------------------------------------

``$ http POST http://localhost:8000/pulp/api/v3/docker-distributions/ name='baz' base_path='foo' publication=$PUBLICATION_HREF``


.. code:: json

    {
        "_href": "/pulp/api/v3/docker-distributions/1/",
       ...
    }

Check status of a task
----------------------

``$ http GET http://localhost:8000/pulp/api/v3/tasks/82e64412-47f8-4dd4-aa55-9de89a6c549b/``

Perform a docker pull from Pulp
-------------------------------

If SSL has not been setup for your Pulp, configure docker to work with the insecure registry:
https://docs.docker.com/registry/insecure/#deploy-a-plain-http-registry

``$ docker pull localhost:8000/foo``
