.. _tagging-untagging-workflow:

Tagging and Untagging Images
============================

Pulp allows its users to add or remove tags of docker images within a repository.

.. _tagging-workflow:

Tagging
-------

Images are described by manifests. The procedure of an image tagging is related to manifests because of that. In pulp, it is required to specify a digest of a manifest in order to create a tag for the corresponding image.

``http POST http://localhost:24817/pulp/api/v3/docker/tag/ repository=${REPOSITORY_HREF} tag=${TAG_NAME} digest=${MANIFEST_DIGEST}``

Each tag has to be unique within a repository to prevent ambiguity. When a user is trying to tag an image with a same name but with a different digest, the tag associated with the old manifest is going to be eliminated in a new repository version. Note that a tagging of same images with existing names still creates a new repository version.

.. _untagging-workflow:

Untagging
---------

An untagging is an inverse operation to the tagging. To remove a tag applied to an image, it is required to issue the following call.

``http POST http://localhost:24817/pulp/api/v3/docker/untag/ repository=${REPOSITORY_HREF} tag=${TAG_NAME}``

Pulp will create a new repository version which will not contain the corresponding tag. The removed tag however still persists in a database. When a client tries to untag an image that was already untagged, a new repository version is created as well.
