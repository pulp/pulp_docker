.. _content-management:

Manage Docker Content in a Repository
=====================================

There are multiple ways that users can manage their Docker content in repositories:

   1. :ref:`Tag<tagging-workflow>` or :ref:`Untag<untagging-workflow>` Manifests in a repository.
   2. :ref:`Recursively add content<recursive-add>`
   3. :ref:`Copy tags from source repository<tag-copy>`

.. warning::

   Users can also add and remove content using the `repository version create endpoint
   <https://docs.pulpproject.org/en/3.0/nightly/restapi.html#operation/repositories_versions_create>`_.
   This endpoint should be reserved for advanced usage and is considered **unsafe** for Docker
   content, because it is not recursive and it allows users to create **corrupted repositories**.

Each of these workflows kicks off a task, and when the task has completed, new repository version
will have been created.

.. _tagging-workflow:

Tagging
-------

Images are described by manifests. The procedure of an image tagging is related to manifests because of that. In pulp, it is required to specify a digest of a manifest in order to create a tag for the corresponding image.

``http POST http://localhost:24817/pulp/api/v3/docker/tag/ repository=${REPOSITORY_HREF} tag=${TAG_NAME} digest=${MANIFEST_DIGEST}``

Each tag has to be unique within a repository to prevent ambiguity. When a user is trying to tag an image with a same name but with a different digest, the tag associated with the old manifest is going to be eliminated in a new repository version. Note that a tagging of same images with existing names still creates a new repository version.

Reference: `Docker Tagging Usage <../restapi.html#tag/docker:-tag>`_

.. _untagging-workflow:

Untagging
---------

An untagging is an inverse operation to the tagging. To remove a tag applied to an image, it is required to issue the following call.

``http POST http://localhost:24817/pulp/api/v3/docker/untag/ repository=${REPOSITORY_HREF} tag=${TAG_NAME}``

Pulp will create a new repository version which will not contain the corresponding tag. The removed tag however still persists in a database. When a client tries to untag an image that was already untagged, a new repository version is created as well.

Reference: `Docker Untagging Usage <../restapi.html#tag/docker:-untag>`_

.. _recursive-add:

Recursively Add Content to a Repository
---------------------------------------

Any Docker content can be added to a repository version with the
recursive-add endpoint. Here, "recursive" means that the content will be
added, as well as all related content.

Relations:
   - Adding a **tag**  will also add the tagged manifest and its related
     content.
   - Adding a **manifest** (manifest list) will also add related
     manifests and their related content.
   - Adding a **manifest** (not manifest list) will also add related
     blobs.

Because tag names are unique within a repository version, adding a tag
with a duplicate name will first remove the existing tag
(non-recursively).

.. note::

   Adding a tagged manifest will **not** include the tag itself.

Reference: `Docker Recursive Add Usage <../restapi.html#tag/docker:-recursive-add>`_

.. _tag-copy:

Recursively Copy Tags from a Source Repository
----------------------------------------------

Tags in one repository can be copied to another repository using the tag
copy endpoint.

When no names are specified, all tags are recursively copied. If names are
specified, only the matching tags are recursively copied.

If tag names being copied already exist in the destination repository,
the conflicting tags are removed from the destination repository and the
new tags are added. This action is not recursive, no manifests or blobs
are removed.

Reference: `Docker Copy Tags Usage <../restapi.html#operation/docker_tags_copy_create>`_
