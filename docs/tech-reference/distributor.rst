Distributor Configuration
=========================


Web Distributor
---------------

Type ID: ``docker_distributor_web``

The Web distributor is used to publish a Docker repository in a way that can be consumed
and served by Crane directly. By default the
:ref:`redirect files <redirect_file>` are stored as
``/var/lib/pulp/published/docker/v1/app/<reponame>.json`` and
``/var/lib/pulp/published/docker/v2/app/<reponame>.json`` for the Docker v1 and
v2 content, respectively. The repo data itself is stored in
``/var/lib/pulp/published/docker/v1/web/<repo_id>/`` and
``/var/lib/pulp/published/docker/v2/web/<repo_id>/``.

The global configuration file for the docker_web_distributor plugin
can be found in ``/etc/pulp/server/plugins.conf.d/docker_distributor.json``.

All values from the global configuration can be overridden on the local config.

Supported keys
^^^^^^^^^^^^^^

``docker_publish_directory``
 The publish directory used for this distributor. The web server should be configured to serve
 ``<publish_directory>/v1/web`` and ``<publish_directory>/v2/web``. The default value is
 ``/var/lib/pulp/published/docker``.

``protected``
 if "true" requests for this repo will be checked for an entitlement certificate authorizing
 the server url for this repository; if "false" no authorization checking will be done.
 This defaults to false.

``redirect-url``
 The server URL that will be used when generating the redirect map for connecting the Docker
 API to the location the content is stored. The value defaults to
 ``https://<server_name_from_pulp_server.conf>/pulp/docker/v1/<repo_name>``.
 This is used for v1 content.

``repo-registry-id``
 The name that should be used for the repository when it is served by Crane. If specified
 it will be used for the ``repository`` field in the :ref:`redirect file <redirect_file>`.
 If a value is not specified, then repository id is used. 


Export Distributor
------------------

Type ID: ``docker_distributor_export``

The export distributor is used to save the contents of a v1 publish into a tar
file that can be moved easily for instances where Crane is running on a
different server than your Pulp instance. By default the
:ref:`redirect file <redirect_file>` is stored in the root of the tar file as
``<reponame>.json``, and the repo data itself is stored in the ``/<repo_id>/`` sub directory of
the tar file.

The global configuration file for the docker_export_distributor plugin
can be found in ``/etc/pulp/server/plugins.conf.d/docker_distributor_export.json``.

All values from the global configuration can be overridden on the local config.

Supported keys
^^^^^^^^^^^^^^

``docker_publish_directory``
 The publish directory used for this distributor. The web server should be configured to serve
 <publish_directory>/export. The default value is ``/var/lib/pulp/published/docker``.

``export_file``
 The fully qualified path and name of the tar file that will be created by the export.
 This defaults to ``<docker_publish_directory>/v1/export/repo/<repo_id>.tar``

``protected``
 if "true" requests for this repo will be checked for an entitlement certificate authorizing
 the server url for this repository; if "false" no authorization checking will be done.

``redirect-url``
 The URL where image files for this repository are served. Crane will join this URL with
 ``<image_id>/<filename>``

``repo-registry-id``
 The name that should be used for the repository when it is served by Crane. If specified
 it will be used for the ``repository`` field in the :ref:`redirect file <redirect_file>`.
 If a value is not specified, then repository id is used. Docker requires that this field
 contains only lower case letters, integers, hyphens, and periods. Additionally a single
 slash can be used to namespace the repo.


.. _redirect_file:

V3 Redirect File
----------------

For Docker v2 content, the distributors generate a json file with the details of the repository
contents.

The file is JSON formatted with the following keys

* **type** *(string)* - the type of file. This will always be "pulp-docker-redirect".
* **version** *(int)* - version of the format for the file. For Docker v2, that supports manifest schema,
                        this will be 3.
* **repository** *(string)* - the name of the repository this file is describing.
* **repo-registry-id** *(string)* - the name that will be used for this repository in the Docker
  registry.
* **url** *(string)* - the URL for accessing the repository content.
* **schema2_data** *(array)* - an array of tags and digests that schema version 2 manifests reference.
* **protected** *(bool)* - whether or not the repository should be protected by an entitlement
  certificate.

Example Redirect File Contents::

 {
  "type":"pulp-docker-redirect",
  "version":3,
  "repository":"docker",
  "repo-registry-id":"redhat/docker",
  "url":"http://www.foo.com/docker",
  "schema2_data":[]}
  "protected": false
 }


V2 Redirect File
----------------

For Docker v2 content, the distributors generate a json file with the details of the repository
contents.

The file is JSON formatted with the following keys

* **type** *(string)* - the type of file. This will always be "pulp-docker-redirect".
* **version** *(int)* - version of the format for the file. For Docker v2, this will be 2.
* **repository** *(string)* - the name of the repository this file is describing.
* **repo-registry-id** *(string)* - the name that will be used for this repository in the Docker
  registry.
* **url** *(string)* - the URL for accessing the repository content.
* **protected** *(bool)* - whether or not the repository should be protected by an entitlement
  certificate.

Example Redirect File Contents::

 {
  "type":"pulp-docker-redirect",
  "version":2,
  "repository":"docker",
  "repo-registry-id":"redhat/docker",
  "url":"http://www.foo.com/docker",
  "protected": false
 }


V1 Redirect File
----------------

For legacy Docker v1 content, the distributors generate a json file with the details of the
repository contents.

The file is JSON formatted with the following keys

* **type** *(string)* - the type of file. This will always be "pulp-docker-redirect".
* **version** *(int)* - version of the format for the file. For Docker v1, this will be 1.
* **repository** *(string)* - the name of the repository this file is describing.
* **repo-registry-id** *(string)* - the name that will be used for this repository in the Docker
  registry.
* **url** *(string)* - the URL for accessing the repository content.
* **protected** *(bool)* - whether or not the repository should be protected by an entitlement
  certificate.
* **images** *(array)* - an array of objects describing each image/layer in the repository.

  * **id** *(str)* - the image id for the image.

* **tags** *(obj)* - an object containing key, value pairs of "tag-name":"image-id".

Example Redirect File Contents::

 {
  "type":"pulp-docker-redirect",
  "version":1,
  "repository":"docker",
  "repo-registry-id":"redhat/docker",
  "url":"http://www.foo.com/docker",
  "protected": false,
  "images":[
    {"id":"48e5f45168b97799ad0aafb7e2fef9fac57b5f16f6db7f67ba2000eb947637eb"},
    {"id":"511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158"},
    {"id":"769b9341d937a3dba9e460f664b4f183a6cecdd62b337220a28b3deb50ee0a02"},
    {"id":"bf747efa0e2fa9f7c691588ce3938944c75607a7bb5e757f7369f86904d97c78"}
    ],
  "tags": {"latest": "769b9341d937a3dba9e460f664b4f183a6cecdd62b337220a28b3deb50ee0a02"}
 }

Docker rsync Distributor
------------------------

Purpose:
--------
The Docker rsync distributor publishes docker content to a remote server. The distributor uses
rsync over ssh to perform the file transfer. Docker images (v1) are published into the root of
the remote repository. Manifests (v2) are published into ``manifests`` directory and Blobs (v2) are
published into ``blobs`` directory.

The docker rsync distributor makes it easier to serve docker content on one server and run Crane on
another server. It is recommended that the rsync distributor is used required to publish prior to
publishing with the docker web distributor.

Configuration
=============
Pulp's SELinux policy includes a ``pulp_manage_rsync`` boolean. When enabled, the
``pulp_manage_rsync`` boolean allows Pulp to use rsync and make ssh connections. The boolean is
disabled by default. The RPM Rsync distributor will fail to publish with SELinux Enforcing unless
the boolean is enabled. To enable it, you can do this::

    $ sudo semanage boolean --modify --on pulp_manage_rsync

Here is an example docker_rsync_distributor configuration::

    {
     "distributor_id": "my_docker_rsync_distributor",
     "distributor_type_id": "docker_rsync_distributor",
     "distributor_config": {
        "remote": {
            "auth_type": "publickey",
            "ssh_user": "foo",
            "ssh_identity_file": "/home/user/.ssh/id_rsa",
            "host": "192.168.121.1",
            "root": "/home/foo/pulp_root_dir"
        },
        "postdistributor_id": "docker_web_distributor_name_cli"
     }
    }


``postdistributor_id``
  The id of the docker_distributor_web associated with the same repository. The
  ``repo-registry-id`` configured in the postdistributor will be used when generating tags list.
  The docker web distributor associated with the same repository is required to have the
  ``predistributor_id`` configured. ``postdistributor_id`` is a required config.

The ``distributor_config`` contains a ``remote`` section with the following settings:

``ssh_user``
  The ssh user for remote server.

``ssh_identity_file``
  Absolute path to the private key that will be used as identity file for ssh. The key must be
  owned by user ``apache`` and must not be readable by other users. If the POSIX permissions are
  too loose, the SSH application will refuse to use the key. Additionally, if SELinux is Enforcing,
  Pulp requires the key to be labeled with the ``httpd_sys_content_t`` SELinux context. This can
  be applied to the file with::

    $ sudo chcon -t httpd_sys_content_t  /path/to/ssh_identity_file

``host``
  The hostname of the remote server.

``root``
  The absolute path to the remote root directory where all the data (content and published content)
  lives. This is the remote equivalent to ``/var/lib/pulp``. The repo id is appended to the
  ``root`` path to determine the location of published repository.

Optional Configuration
----------------------

``content_units_only``
  If true, the distributor will publish content units only (e.g. ``/var/lib/pulp/content``). The
  symlinks of a published repository will not be rsynced.

``delete``
  If true, ``--delete`` is appended to the rsync command for symlinks and repodata so that any old
  files no longer present in the local published directory are removed from the remote server.

``remote_units_path``
  The relative path from the ``root`` where unit files will live. Defaults to ``content/units``.

``relative_repo_path``
  The relative path from the ``root`` where the repository will be published. Defaults to the repository id.

``rsync_extra_args``
  list of strings that can be used to extend default arguments used for rsync call
