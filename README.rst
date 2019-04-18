``pulp_docker`` Plugin
===============================

This is the ``pulp_docker`` Plugin for `Pulp Project
3.0+ <https://pypi.python.org/pypi/pulpcore/>`__. This plugin provides Pulp with support for docker
images, similar to the ``pulp_docker`` plugin for Pulp 2.

All REST API examples below use `httpie <https://httpie.org/doc>`__ to
perform the requests.

``$ sudo dnf install httpie``

To avoid having to pass auth information for each request add the following to ``~/.netrc`` file.

.. code-block:: text

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
   django-admin runserver 24817


Install ``pulp_docker`` From PyPI
------------------------------------------

.. code-block:: bash

   sudo -u pulp -i
   source ~/pulpvenv/bin/activate
   pip install pulp-docker
   django-admin runserver 24817


Make and Run Migrations
-----------------------

.. code-block:: bash

   export DJANGO_SETTINGS_MODULE=pulpcore.app.settings
   django-admin makemigrations docker
   django-admin migrate docker

Run Services
------------

.. code-block:: bash

   django-admin runserver 24817
   gunicorn pulpcore.content:server --bind 'localhost:24816' --worker-class 'aiohttp.GunicornWebWorker' -w 2
   sudo systemctl restart pulp-resource-manager
   sudo systemctl restart pulp-worker@1
   sudo systemctl restart pulp-worker@2


Create a repository ``foo``
---------------------------

``$ http POST http://localhost:24817/pulp/api/v3/repositories/ name=foo``

.. code:: json

    {
        "_href": "/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/",
        ...
    }

``$ export REPO_HREF=$(http :24817/pulp/api/v3/repositories/ | jq -r '.results[] | select(.name == "foo") | ._href')``

Create a new remote ``bar``
---------------------------

``$ http POST http://localhost:24817/pulp/api/v3/remotes/docker/docker/ name='library/busybox' upstream_name='busybox' url='https://registry-1.docker.io'``

.. code:: json

    {
        "_href": "/pulp/api/v3/remotes/docker/docker/f300a4a2-1348-4fce-9836-824203e5130e/",
        ...
    }

``$ export REMOTE_HREF=$(http :24817/pulp/api/v3/remotes/docker/docker/ | jq -r '.results[] | select(.name == "library/busybox") | ._href')``


Sync repository ``foo`` using Remote ``bar``
----------------------------------------------

``$ http POST ':24817'$REMOTE_HREF'sync/' repository=$REPO_HREF``

Look at the new Repository Version created
------------------------------------------

``$ http GET ':24817'$REPO_HREF'versions/1/'``

.. code:: json

    {
        "_created": "2019-03-26T15:54:06.448675Z",
        "_href": "/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/versions/1/",
        "base_version": null,
        "content_summary": {
            "added": {
                "docker.manifest": {
                    "count": 37,
                    "href": "/pulp/api/v3/content/docker/manifests/?repository_version_added=/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/versions/1/"
                },
                "docker.manifest-blob": {
                    "count": 74,
                    "href": "/pulp/api/v3/content/docker/blobs/?repository_version_added=/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/versions/1/"
                },
                "docker.manifest-list": {
                    "count": 10,
                    "href": "/pulp/api/v3/content/docker/manifest-lists/?repository_version_added=/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/versions/1/"
                },
                "docker.manifest-list-tag": {
                    "count": 16,
                    "href": "/pulp/api/v3/content/docker/manifest-list-tags/?repository_version_added=/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/versions/1/"
                }
            },
            "present": {
                "docker.manifest": {
                    "count": 37,
                    "href": "/pulp/api/v3/content/docker/manifests/?repository_version=/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/versions/1/"
                },
                "docker.manifest-blob": {
                    "count": 74,
                    "href": "/pulp/api/v3/content/docker/blobs/?repository_version=/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/versions/1/"
                },
                "docker.manifest-list": {
                    "count": 10,
                    "href": "/pulp/api/v3/content/docker/manifest-lists/?repository_version=/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/versions/1/"
                },
                "docker.manifest-list-tag": {
                    "count": 16,
                    "href": "/pulp/api/v3/content/docker/manifest-list-tags/?repository_version=/pulp/api/v3/repositories/39520001-18e9-4c17-a703-2963a7837060/versions/1/"
                }
            },
            "removed": {}
        },
        "number": 1
    }


Add a Docker Distribution to serve the latest Repository Version
----------------------------------------------------------------

The Docker Distribution will serve the latest version of a Repository if the repository is
specified during creation/update of a Docker Distribution. The Docker Distribution will serve
a specific repository version if repository_version is provided when creating a Docker
Distribution. Either repository or repository_version can be set on a Docker Distribution, but not
both.

``$ http POST http://localhost:24817/pulp/api/v3/docker-distributions/ name='baz' base_path='foo' repository=$REPO_HREF``

.. code:: json

    {
        "_href": "/pulp/api/v3/docker-distributions/8f312746-9b0a-4dda-a9d0-de39f4f43c29/",
       ...
    }

Check status of a task
----------------------

``$ http GET http://localhost:24817/pulp/api/v3/tasks/82e64412-47f8-4dd4-aa55-9de89a6c549b/``

Perform a pull from Pulp
------------------------

Podman 
^^^^^^

``$ podman pull localhost:24816/foo``

If SSL has not been setup for your Pulp, configure podman to work with the insecure registry:

Edit the file ``/etc/containers/registries.conf.`` and add::

    [registries.insecure]
    registries = ['localhost:24816']

More info:
https://www.projectatomic.io/blog/2018/05/podman-tls/ 

Docker 
^^^^^^

``$ docker pull localhost:24816/foo``

If SSL has not been setup for your Pulp, configure docker to work with the insecure registry:

Edit the file ``/etc/docker/daemon.json`` and add::

    {
        "insecure-registries" : ["localhost:24816"]
    }

More info:
https://docs.docker.com/registry/insecure/#deploy-a-plain-http-registry

Release Notes 4.0
-----------------

pulp-docker 4.0 is currently in Beta. Backwards incompatible changes might be made until Beta is over.

4.0.0b3
^^^^^^^

- Enable sync from gcr and quay registries
- Enable support to handle pagination for tags/list endpoint during sync
- Enable support to manage a docker image that has manifest schema v2s1
- Enable docker distribution to serve directly latest repository version

`Comprehensive list of changes and bugfixes for beta 3 <https://github.com/pulp/pulp_docker/compare/4.0.0b2...4.0.0b3>`_.

4.0.0b2
^^^^^^^

- Compatibility with pulpcore-plugin-0.1.0rc1
- Performance improvements and bug fixes
- Add support for syncing repo with foreign layers
- Change sync pipeline to use Futures to handle nested content
- Make Docker distributions asyncronous
- Add support to create publication directly

4.0.0b1
^^^^^^^

- Add support for basic sync of a docker repo form a V2Registry
- Add support for docker/podman pull from a docker distbution served by Pulp
