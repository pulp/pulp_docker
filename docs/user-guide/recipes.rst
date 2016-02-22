Recipes
=======

.. _Crane: https://github.com/pulp/crane

.. _README: https://github.com/pulp/crane/blob/master/README.rst

Configuring Crane with pulp_docker
----------------------------------
The `Crane`_ project can be used to make Docker repositories hosted by Pulp available
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

.. note::

    As of the time of this writing, ``docker save`` can only output Docker v1
    content. Thus, only Docker v1 content can be uploaded to Pulp for now. In
    order to get your own Docker v2 content into Pulp, it is possible to run
    your own Docker registry and point Pulp's feed URL at it and synchronize.

To upload a Docker Image to Pulp, first you must save its repository with Docker.
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
