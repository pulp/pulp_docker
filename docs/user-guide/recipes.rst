Recipes
=======

.. _Crane: https://github.com/pulp/crane

Configuring `Crane`_ with pulp_docker
-------------------------------------
The Crane project can be used to make docker repositories hosted by Pulp available
to the docker client. This allows a ``docker pull`` to be performed against data
that is published by the Pulp server.

If `Crane`_ is being run on the same server that is running Pulp, there is one setting that
must be configured in Crane in order for it to find the information that is published by Pulp.
In the /etc/crane.conf the ``data_dir`` parameter must be set to the location that the pulp publish
is placing metadata files. By default this is the ``/var/lib/pulp/published/docker/app/``
directory. Crane will check the ``data_dir`` for updates periodically.
Full documentation for /etc/crane.conf can be found in the `Crane`_ readme.


Upload To Pulp
--------------

To upload a docker image to pulp, first you must save its repository with docker.
Note that the below command saves all of the images and tags in the ``busybox``
repository to a tarball::

    $ sudo docker pull busybox
    $ sudo docker save busybox > busybox.tar

Then create a pulp repository and run an upload command with ``pulp-admin``::

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
    cancelled entirely using the cancel command.

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


There are now four new images in the pulp repository::

    $ pulp-admin docker repo list
    +----------------------------------------------------------------------+
                              Docker Repositories
    +----------------------------------------------------------------------+

    Id:                  busybox
    Display Name:        busybox
    Description:         None
    Content Unit Counts:
      Docker Image: 4


During an image upload, you can specify the id of an ancestor image
that should not be uploaded to the repository. In this case, the masked ancestor
and any ancestors of that image will not be imported::

    $ pulp-admin docker repo create --repo-id tutorial
    Repository [tutorial] successfully created

    $ pulp-admin docker repo uploads upload --repo-id tutorial
    -f /home/skarmark/git/pulp1/pulp/tutorial.tar
    --mask-ancestor-id 'f38e479062c4953de709cc7f08fa8f85bec6bc5d01f03e340f7caf2990e8efd1'
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
    cancelled entirely using the cancel command.

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

There are now only two images imported into the pulp repository, instead of five total images
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


Publish
-------

The ``busybox`` repository uploaded above can be published for use with `Crane`_.

First the docker repository name must be specified, which can
be different than the ``repo_id``. The repository name should usually have a
namespace, a ``/``, and then a name. The command below sets the repository name
to ``pulpdemo/busybox``::

    $ pulp-admin docker repo update --repo-id=busybox --repo-registry-id=pulpdemo/busybox
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

    $ pulp-admin docker repo publish run --repo-id=busybox
    +----------------------------------------------------------------------+
                        Publishing Repository [busybox]
    +----------------------------------------------------------------------+

    This command may be exited via ctrl+c without affecting the request.


    Publishing Image Files.
    [==================================================] 100%
    4 of 4 items
    ... completed

    Making files available via web.
    [-]
    ... completed


    Task Succeeded


`Crane`_ can now be run on the same machine serving the docker repository through
its docker-registry-like read-only API.

Export
------

The ``busybox`` repository can also be exported for a case where `Crane`_ will
be run on a different machine, or the image files will be hosted by another
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

This produces a tarball at ``/var/lib/pulp/published/docker/export/repo/busybox.tar``
which contains both a JSON file for use with crane, and the static image files
to which crane will redirect requests. See the `Crane`_ documentation for how
to use that tarball.

Sync
------

The pulp-docker plugin supports syncing from upstream repositories as of version 0.2.1. For example::

    $ pulp-admin docker repo create synctest --feed=https://index.docker.io --upstream-name=busybox
    Repository [synctest] successfully created

    $ pulp-admin docker repo sync run --repo-id synctest
    +----------------------------------------------------------------------+
                        Synchronizing Repository [synctest]
    +----------------------------------------------------------------------+

    This command may be exited via ctrl+c without affecting the request.


    Retrieving metadata
    [\]
    ... completed

    Copying units already in pulp
    [-]
    ... completed

    Downloading remote files
    [-]
    ... completed

    Saving images and tags
    [-]
    ... completed


    Task Succeeded

Once this is complete, the data in the remote repository is now in your local Pulp instance.
