Recipes
=======

.. _Crane: https://github.com/pulp/crane

.. _README: https://github.com/pulp/crane/blob/master/README.rst

Configuring Crane with pulp_docker
----------------------------------
The `Crane`_ project is meant to be used to make Docker repositories hosted by Pulp available
to the Docker client. This allows a ``docker pull`` to be performed against data
that is published by the Pulp server.

If Crane is being run on the same server that is running Pulp, there is one setting that
must be configured in Crane in order for it to find the information that is published by Pulp.
In the /etc/crane.conf the ``data_dir`` parameter must be set to a location that
contains the app files that are generated during Pulp publish operations.

Pulp places these files in two locations, one for each version of Docker:
``/var/lib/pulp/published/docker/v1/app/`` and
``/var/lib/pulp/published/docker/v2/app/``. If you only plan to use one version
of Docker content, you can set Crane's ``data_dir`` setting to point at the
appropriate path. If you plan to serve both, Crane can scan the whole
``/var/lib/pulp/published/docker`` path, filtering for ``*.json`` files. Crane
will check the ``data_dir`` for updates periodically.

.. note::

   As mentioned above, Crane is able to serve both content version V1 and V2, though it is
   required to have installed proper docker client version which will be capable to fetch the content.
   Bear in mind that in newer docker client versions, interaction with V1 registries is deprecated, and
   since version 1.13 support for the V1 protocol is removed.
   For more info check `docker docs <https://docs.docker.com/engine/deprecated/#interacting-with-v1-registries>`_

Full documentation for /etc/crane.conf can be found in the Crane `README`_.


Sync
----

The pulp-docker plugin supports synchronizing from upstream repositories as of
version 0.2.1. As of version 2.0.0, it can synchronize with either Docker v1 or
v2 registries.

.. note::

    ``registry-1.docker.io`` is a Docker V2 Registry API. For V1 API
    ``index.docker.io`` should be used, along with ``--enable-v1 true`` and
    ``--enable-v2 false``. Please note however that V1 content is deprecated
    and Docker may remove it at any time.

::

    $ pulp-admin docker repo create --repo-id=synctest --feed=https://registry-1.docker.io --upstream-name=busybox
    Repository [synctest] successfully created

    $ pulp-admin docker repo sync run --repo-id synctest
    +----------------------------------------------------------------------+
                      Synchronizing Repository [synctest]
    +----------------------------------------------------------------------+

    This command may be exited via ctrl+c without affecting the request.


    Downloading manifests
    [\]
    ... completed

    Copying units already in pulp
    [-]
    ... completed

    Copying units already in pulp
    [-]
    ... completed

    Downloading remote files
    [==================================================] 100%
    11 of 11 items
    ... completed

    Saving Manifests and Blobs
    [-]
    ... completed

    Saving Tags
    [-]
    ... completed


    Task Succeeded




    Task Succeeded


Once this is complete, the data in the remote repository is now in your local Pulp instance.

As mentioned, it is still possible to synchronize Docker v1 content if you use
the old feed URL and enable/disable v1/v2::

    $ pulp-admin docker repo create --repo-id=v1synctest --feed=https://index.docker.io --upstream-name=busybox --enable-v1 true --enable-v2 false
    Repository [v1synctest] successfully created

    $ pulp-admin docker repo sync run --repo-id v1synctest
    +----------------------------------------------------------------------+
                     Synchronizing Repository [v1synctest]
    +----------------------------------------------------------------------+

    This command may be exited via ctrl+c without affecting the request.


    Retrieving v1 metadata
    [-]
    ... completed

    Copying units already in pulp
    [-]
    ... completed

    Downloading remote files
    [==================================================] 100%
    53 of 53 items
    ... completed

    Saving v1 images and tags
    [-]
    ... completed


    Task Succeeded




    Task Succeeded


Publish
-------

The repositories created above can be published for use with `Crane`_.

First the Docker repository name must be specified, which can
be different than the ``repo_id``. The repository name should usually have a
namespace, a ``/``, and then a name. Other than the slash between the namespace and the name,
it is required that this field can contain only lower case letters, integers, hyphens, and periods.
The command below sets the repository name
to ``pulpdemo/synctest``::

    $ pulp-admin docker repo update --repo-id=synctest --repo-registry-id=pulpdemo/synctest
    This command may be exited via ctrl+c without affecting the request.


    [\]
    Running...
    Updating distributor: docker_web_distributor_name_cli

    Task Succeeded



    [\]
    Running...
    Updating distributor: docker_export_distributor_name_cli

    Task Succeeded

Then a publish operation can be executed::

    $ pulp-admin docker repo publish run --repo-id=synctest
    +----------------------------------------------------------------------+
                        Publishing Repository [synctest]
    +----------------------------------------------------------------------+

    This command may be exited via ctrl+c without affecting the request.



    Task Succeeded

`Crane`_ can now be run on the same machine serving the Docker repository through
its Docker-registry-like read-only API.


Upload v1 Images to Pulp
------------------------

To upload a Docker v1 Image to Pulp, first you must save its repository with Docker.
Note that the below command saves all of the Images and tags in the ``busybox``
repository to a tarball::

    $ sudo docker pull busybox
    $ sudo docker save busybox > busybox.tar

Then create a Pulp repository and run an upload command with ``pulp-admin``::

    $ pulp-admin docker repo create --repo-id=busybox
    Repository [busybox] successfully created

    $ pulp-admin docker repo uploads upload --repo-id=busybox -f busybox.tar
    +----------------------------------------------------------------------+
                                  Unit Upload
    +----------------------------------------------------------------------+

    Extracting necessary metadata for each request...
    [==================================================] 100%
    Analyzing: busybox.tar
    ... completed

    Creating upload requests on the server...
    [==================================================] 100%
    Initializing: busybox.tar
    ... completed

    Starting upload of selected units. If this process is stopped through ctrl+c,
    the uploads will be paused and may be resumed later using the resume command or
    canceled entirely using the cancel command.

    Uploading: busybox.tar
    [==================================================] 100%
    2825216/2825216 bytes
    ... completed

    Importing into the repository...
    This command may be exited via ctrl+c without affecting the request.


    [\]
    Running...

    Task Succeeded


    Deleting the upload request...
    ... completed


There are now Images in the Pulp repository::

    $ pulp-admin docker repo list
    +----------------------------------------------------------------------+
                              Docker Repositories
    +----------------------------------------------------------------------+

    Id:                  busybox
    Display Name:        busybox
    Description:         None
    Content Unit Counts:
      Docker Image: 4

.. note::

    The number of Images associated with the repository at this point may differ
    from the number seen above, but should be at least 1 Image.


During an Image upload, you can specify the id of an ancestor Image
that should not be uploaded to the repository. In this case, the masked ancestor
and any ancestors of that Image will not be imported::

    $ pulp-admin docker repo create --repo-id tutorial
    Repository [tutorial] successfully created

    $ pulp-admin docker repo uploads upload --repo-id tutorial
    -f /home/skarmark/git/pulp1/pulp/tutorial.tar
    --mask-id 'f38e479062c4953de709cc7f08fa8f85bec6bc5d01f03e340f7caf2990e8efd1'
    +----------------------------------------------------------------------+
                              Unit Upload
    +----------------------------------------------------------------------+

    Extracting necessary metadata for each request...
    [==================================================] 100%
    Analyzing: tutorial.tar
    ... completed

    Creating upload requests on the server...
    [==================================================] 100%
    Initializing: tutorial.tar
    ... completed

    Starting upload of selected units. If this process is stopped through ctrl+c,
    the uploads will be paused and may be resumed later using the resume command or
    canceled entirely using the cancel command.

    Uploading: tutorial.tar
    [==================================================] 100%
    353358336/353358336 bytes
    ... completed

    Importing into the repository...
    This command may be exited via ctrl+c without affecting the request.


    [\]
    Running...

    Task Succeeded


    Deleting the upload request...
    ... completed

There are now only two Images imported into the Pulp repository, instead of five total Images
in the tar file::

    $ pulp-admin docker repo list
    +----------------------------------------------------------------------+
                            Docker Repositories
    +----------------------------------------------------------------------+

    Id:                  tutorial
    Display Name:        tutorial
    Description:         None
    Content Unit Counts:
        Docker Image: 2


v1 Export
---------

The ``busybox`` repository can also be exported for a case where `Crane`_ will
be run on a different machine, or the Image files will be hosted by another
service::

    $ pulp-admin docker repo export run --repo-id=busybox
    +----------------------------------------------------------------------+
                        Publishing Repository [busybox]
    +----------------------------------------------------------------------+

    This command may be exited via ctrl+c without affecting the request.


    Publishing Image Files.
    [==================================================] 100%
    4 of 4 items
    ... completed

    Saving tar file.
    [-]
    ... completed


    Task Succeeded

.. note::

    The number of Images that get published when you try this may differ
    from the number seen above, but should be at least 1 Image.

This produces a tarball at
``/var/lib/pulp/published/docker/v1/export/repo/busybox.tar`` which contains
both a JSON file for use with crane, and the static Image files to which crane
will redirect requests. See the `Crane`_ documentation for how to use that
tarball.

Upload v2 schema 2 Images to Pulp
---------------------------------

.. note::

    As of the time of this writing, ``skopeo copy`` can only output Docker v2
    schema 2 content. Thus, only Docker v2 schema 2 content can be uploaded
    to Pulp for now. In order to get your own Docker v2 schema 1 content into
    Pulp, it is possible to run your own Docker registry and point Pulp's
    feed URL at it and synchronize.

To upload a Docker Image to Pulp, first you must save its repository with Skopeo.
Note that the below command saves the image in the ``busybox``
repository to a directory::

    $ sudo docker pull busybox
    $ sudo skopeo copy docker://busybox:latest dir:existingemptydirectory

Before uploading the image to a Pulp repository, you need to create a tarball
with the directory contents created by ``skopeo copy``::

    $ cd directory-name && tar -cvf ../image-name.tar * && cd ..

Then create a Pulp repository and run an upload command with ``pulp-admin``::

    $ pulp-admin docker repo create --repo-id=skopeo
    Repository [skopeo] successfully created

    $ pulp-admin docker repo uploads upload --repo-id=skopeo -f skopeo.tar
    +----------------------------------------------------------------------+
                              Unit Upload
    +----------------------------------------------------------------------+

    Extracting necessary metadata for each request...
    [==================================================] 100%
    Analyzing: skopeo.tar
    ... completed

    Creating upload requests on the server...
    [==================================================] 100%
    Initializing: skopeo.tar
    ... completed

    Starting upload of selected units. If this process is stopped through ctrl+c,
    the uploads will be paused and may be resumed later using the resume command or
    canceled entirely using the cancel command.

    Uploading: skopeo.tar
    [==================================================] 100%
    727040/727040 bytes
    ... completed

    Importing into the repository...
    This command may be exited via ctrl+c without affecting the request.


    [\]
    Running...

    Task Succeeded


    Deleting the upload request...
    ... completed


The Blobs and Manifest are now in the Pulp repository::

    +----------------------------------------------------------------------+
                              Docker Repositories
    +----------------------------------------------------------------------+

    Id:                  skopeo
    Display Name:        None
    Description:         None
    Content Unit Counts:
        Docker Blob:     2
        Docker Manifest: 1

.. note::

    ``skopeo copy`` looses all the tags in the repository, therefore the manifests
    need to be tagged as a separate step after uploading it.

Uploading a Manifest List
-------------------------

Manifests referenced by the Manifest List must already be associated to
the target repository. For this example, start with a synced busybox
repository.::

   $ pulp-admin docker repo sync run --repo-id busybox

To upload your Manifest List, use the ``upload`` command::

   $ pulp-admin docker repo uploads upload --repo-id=busybox --manifest-list -f your_manifest_list.json
   +----------------------------------------------------------------------+
                                 Unit Upload
   +----------------------------------------------------------------------+

   Extracting necessary metadata for each request...
   [==================================================] 100%
   Analyzing: your_manifest_list.json
   ... completed

   Creating upload requests on the server...
   [==================================================] 100%
   Initializing: your_manifest_list.json
   ... completed

   Starting upload of selected units. If this process is stopped through ctrl+c,
   the uploads will be paused and may be resumed later using the resume command or
   canceled entirely using the cancel command.

   Uploading: your_manifest_list.json
   [==================================================] 100%
   1358/1358 bytes
   ... completed

   Importing into the repository...
   This command may be exited via ctrl+c without affecting the request.


   [\]
   Running...

   Task Succeeded


   Deleting the upload request...
   ... completed


Tagging a Manifest
------------------

Using the ``docker repo tag`` command, we can point a docker tag to a manifest. If
the tag we specify does not exist, it will be created. If the tag exists
however, it will be updated as tag name is unique per repository and can point
to only one manifest.

.. note::

    Pulp now supports image manifest schema 1 and schema 2 versions, same as manifest lists schema 2.
    So when tagging a manifest( image or list), bear in mind that within a repo there could be two
    tags with the same name but pointing to manifests with different schema versions.


For instance, suppose we have the following image manifest that is tagged ::

    pulp-admin docker repo search tag --repo-id man-list --str-eq='name=uclibc'

    Created:      2017-07-12T11:43:29Z
    Metadata:
      Manifest Digest:    sha256:26b0ddb0504097612cd7ed2265eade43f2490cd111a7cfcf7d1
                          51dba83b20a5e
      Manifest Type:      image
      Name:               uclibc
      Pulp User Metadata:
      Repo Id:            man-list
      Schema Version:     1
    Repo Id:      man-list
    Unit Id:      a37aa675-194c-4f07-925b-e1e12d98ad85
    Unit Type Id: docker_tag
    Updated:      2017-07-12T11:43:29Z

If we have a tag named uclibc and it points to the manifest with digest
sha256:26b0ddb0..., we can point it to the new manifest with the following
command::

    $ pulp-admin docker repo tag --repo-id busybox --tag-name latest --digest sha256:c152ddeda2b828fbb610cb9e4cb121e1879dd5301d336f0a6c070b2844a0f56d

We can also create a new tag and point it to the same manifest with::

    $ pulp-admin docker repo tag --repo-id busybox --tag-name 1.2 --digest sha256:c152ddeda2b828fbb610cb9e4cb121e1879dd5301d336f0a6c070b2844a0f56d


Copy
----

The ``docker repo copy`` command can be used to copy docker v1 and v2 content.
In this recipe, we will go through the copy process of different docker content types ::

    $ pulp-admin docker repo list

    +----------------------------------------------------------------------+
                              Docker Repositories
    +----------------------------------------------------------------------+

    Id:                  containers
    Display Name:        None
    Description:         None
    Content Unit Counts:
      Docker Blob:          93
      Docker Manifest:      115
      Docker Manifest List: 4
      Docker Tag:           128

    Id:                  containers2
    Display Name:        None
    Description:         None
    Content Unit Counts:


Let's copy all image manifests from repo `containers` to the destination repo `containers2` ::

    $ pulp-admin docker repo copy manifest --from-repo-id containers --to-repo-id containers2

    This command may be exited via ctrl+c without affecting the request.


    [|]
    Running...

    Copied:
      docker_blob: 93
      docker_manifest: 115


As you can see during the copy of image manifests, all referenced blobs were carried over as well.
Note that tags are lost during the copy of the manifests.

  ::
    $ pulp-admin docker repo copy

    Usage: pulp-admin [SUB_SECTION, ..] COMMAND
    Description: content copy commands

    Available Commands:
      image         - copies images from one repository into another
      manifest      - copies manifests from one repository into another
      manifest-list - copies manifest lists from one repository into another
      tag           - copies tags from one repository into another


* If a manifest list is copied, all listed image manifests within the manifest list and blobs
  will be carried over. Tags of image manifests will not be copied.
* If a tag which references an image manifest is copied, image manifest and all its blobs will
  be copied over.
* If a tag which references a manifest list is copied, the manifest list, all listed image manifests
  within the manifest list and blobs will be carried over. Tags of images manifests will not be copied.


Remove
------

The ``docker repo remove`` command can be used to remove docker v1 and v2 content from the repository.
In this recipe, we will go through the removal process of different docker content types.

Let's remove a tag with the name `latest` ::

    $ pulp-admin docker repo remove tag --repo-id containers --str-eq=name=latest

    This command may be exited via ctrl+c without affecting the request.


    [\]
    Running...

    Units Removed:
      latest
      latest

There were removed two tags with the name `latest` because one tag was referencing an image manifest
and the second tag was referencing a manifest list.

In case it is desired to remove a specific tag which references, for example, manifest list, then `manifest type` should be specified ::

    $ pulp-admin docker repo remove tag --repo-id containers --str-eq=name=glibc --str-eq='manifest_type=list'

    This command may be exited via ctrl+c without affecting the request.


    [\]
    Running...

    Units Removed:
      glibc

  ::

    $ pulp-admin docker repo remove

    Usage: pulp-admin [SUB_SECTION, ..] COMMAND
    Description: content removal commands

    Available Commands:
      image         - remove images from a repository
      manifest      - remove manifests from a repository
      manifest-list - remove manifest lists from a repository
      tag           - remove tags from a repository

* If a tag is removed, just the tag itself will be removed from the repository.
* If a manifest list is removed, all its image manifests which don't have tags and are not
  referenced in any other manifest list will be removed from the repo. Orphaned blobs from removed
  image manifests will be removed as well.
* If an image manifest is removed, all its blobs, which are not referenced in any other image
  manifests within the repo, will be removed as well.

.. warning::
    Please make sure that when you remove an image manifest, it is not referenced in any manifest
    lists within the repo, otherwise you risk to corrupt a manifest list.
