Concepts
========

Docker v2 Concepts
------------------

Repository and Tags
^^^^^^^^^^^^^^^^^^^

A Docker v2 repository is a collection of Blobs, Image Manifests, Manifest Lists
and Tags. Blobs are the layers that together make up a Docker image. The Image
Manifest is the metadata that connects the Blobs together in the correct order,
and it can also contain other metadata such as signatures. A Manifest List is
a list of Image manifests for one or more platforms. An Image Manifest or
Manifest Listcan be tagged in a repository, and the Tag object is how this is
accomplished in Pulp. So in short, a Tag references one Manifest(image or list)
by digest same for a Image Manifest which references N Blobs (also by digest).

.. note::

    Tags are a repository property in v1, but are a full Unit in v2.

.. note::

    In Docker v2, Manifest v1 schemas contain a ``tag`` field which is not
    unique per repository. When determining what Manifest is associated with
    what Tag name, users should rely on the ``name`` and ``manifest_digest``
    fields for Tag Units and not the Manifest ``tag`` field. In the Manifest v2
    schema, the ``tag`` field has been removed.
    Since 3.0 fields ``tag`` and ``name`` and removed completely from Manifest model.

Upload
^^^^^^

.. _distribution container: https://github.com/docker/distribution

Unfortunately, Docker has not provided a ``docker save`` command that can
output Docker v2 content. However, if you wish to upload a Docker v2 schema 2 image, then you could use ``skopeo
copy`` command to create an on-disk representation of the image and later upload it after tarring it.
Other option is to push it into Docker's `distribution container`_, and then
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
