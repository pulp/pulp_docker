Concepts
========

Docker v2 Concepts
------------------

Repository and Tags
^^^^^^^^^^^^^^^^^^^

A Docker v2 repository is a collection of Blobs, Manifests, and Tags. Blobs are
the layers that together make up a Docker image. The Manifest is the metadata
that connects the Blobs together in the correct order, and it can also contain
other metadata such as signatures. A Manifest can be tagged in a repository, and
the Tag object is how this is accomplished in Pulp. So in short, a Tag
references one Manifest (by digest) and a Manifest references N Blobs
(also by digest).

.. note::

    Tags are a repository property in v1, but are a full Unit in v2.

Upload
^^^^^^

.. _distribution container: https://github.com/docker/distribution

Unfortunately, Docker has not provided a ``docker save`` command that can
output Docker v2 content. Due to this, Pulp does not support uploading Docker
v2 content at this time. If you wish to add your own custom v2 content into
Pulp, you will need to push it into Docker's `distribution container`_, and then
synchronize a Pulp repository with the local registry.


Docker v1 Concepts
------------------

Repository and Tags
^^^^^^^^^^^^^^^^^^^

A Docker v1 repository is a collection of Images that can have tags. A Pulp
repository likewise is a collection of Docker Images. Tags are a property of the
repository and can be modified with the command ``pulp-admin docker repo update``
and its ``--tag`` option.

.. note::

    Tags are a repository property in v1, but are a full Unit in v2.

Upload
^^^^^^

An upload operation potentially includes multiple layers. When doing a
``docker save``, a tarball is created with the requested repository and all of
its ancestor layers. When uploading that tarball to Pulp, each layer will be
added to the repository as a unit. The tags will also be added to the
repository, overwriting any previous tags of the same name.
