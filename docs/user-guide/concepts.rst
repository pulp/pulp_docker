Concepts
========

Repository and Tags
-------------------

A docker repository is a collection of images that can have tags. A pulp
repository likewise is a collection of docker images. Tags are a property of the
repository and can be modified with the command ``pulp-admin docker repo update``
and its ``--tag`` option.

Upload
------

An upload operation potentially includes multiple layers. When doing a
``docker save``, a tarball is created with the requested repository and all of
its ancestor layers. When uploading that tarball to pulp, each layer will be
added to the repository as a unit. The tags will also be added to the
repository, overwriting any previous tags of the same name.
