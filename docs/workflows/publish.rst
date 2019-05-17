Publish and Host
================

This section assumes that you have a repository with content in it. To do this, see the
:doc:`sync` or :doc:`upload` documentation.

Create a Docker Distribution to serve your Repository Version
-------------------------------------------------------------

The Docker Distribution will serve the latest version of a Repository if the repository is
specified during creation/update of a Docker Distribution. The Docker Distribution will serve
a specific repository version if repository_version is provided when creating a Docker
Distribution. Either repository or repository_version can be set on a Docker Distribution, but not
both.

Create the distribution, referencing a repository or repository version::

    $ http POST http://localhost:8000/pulp/api/v3/distributions/docker/docker/ name='baz' base_path='foo' repository=$REPOSITORY_HREF

Response:

.. code:: json

    {
        "_href": "/pulp/api/v3/docker-distributions/8f312746-9b0a-4dda-a9d0-de39f4f43c29/",
       ...
    }

Reference: `Docker Distribution Usage <../restapi.html#tag/distributions>`_

Check status of a task
----------------------

``$ http GET http://localhost:8000/pulp/api/v3/tasks/82e64412-47f8-4dd4-aa55-9de89a6c549b/``

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
