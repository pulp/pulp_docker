Distributor Configuration
=========================


Web Distributor
---------------

Type ID: ``docker_distributor_web``

The Web distributor is used to publish a docker repository in a way that can be consumed
and served by Crane directly. By default the :ref:`redirect file <redirect_file>` is stored as
``/var/lib/pulp/published/docker/app/<reponame>.json``, and the repo data itself is stored in
``/var/lib/pulp/published/docker/web/<repo_id>/``.

The global configuration file for the docker_web_distributor plugin
can be found in ``/etc/pulp/server/plugins.conf.d/docker_distributor.json``.

All values from the global configuration can be overridden on the local config.

Supported keys
^^^^^^^^^^^^^^

``docker_publish_directory``
 The publish directory used for this distributor. The web server should be configured to serve
 <publish_directory>/web. The default value is ``/var/lib/pulp/published/docker``.

``protected``
 if "true" requests for this repo will be checked for an entitlement certificate authorizing
 the server url for this repository; if "false" no authorization checking will be done.
 This defaults to true.

``redirect-url``
 The server URL that will be used when generating the redirect map for connecting the docker
 API to the location the content is stored. The value defaults to
 ``https://<server_name_from_pulp_server.conf>/pulp/docker/<repo_name>``.

``repo-registry-id``
 The name that should be used for the repository when it is served by Crane. If specified
 it will be used for the ``repository`` field in the :ref:`redirect file <redirect_file>`.
 If a value is not specified, then repository id is used.


Export Distributor
------------------

Type ID: ``docker_distributor_export``

The export distributor is used to save the contents of a publish into a tar file that can be
moved easily for instances where Crane is running on a different server than your pulp instance.
By default the :ref:`redirect file <redirect_file>` is stored in the root of the tar file as
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
 This defaults to ``<docker_publish_directory>/export/repo/<repo_id>.tar``

``protected``
 if "true" requests for this repo will be checked for an entitlement certificate authorizing
 the server url for this repository; if "false" no authorization checking will be done.

``redirect-url``
 The URL where image files for this repository are served. Crane will join this URL with
 ``<image_id>/<filename>``

``repo-registry-id``
 The name that should be used for the repository when it is served by Crane. If specified
 it will be used for the ``repository`` field in the :ref:`redirect file <redirect_file>`.
 If a value is not specified, then repository id is used.


.. _redirect_file:

Redirect File
-------------

The distributors generate a json file with the details of the repository contents.

The file is JSON formatted with the following keys

* **type** *(string)* - the type of the file. This will always be "pulp-docker-redirect"
* **version** *(int)* - version of the format for the file. Currently version 1
* **repository** *(string)* - the name of the repository this file is describing
* **repo-registry-id** *(string)* - the name that will be used for this repository in the Docker
  registry
* **url** *(string)* - the url for access to the repositories content
* **protected** *(bool)* - whether or not the repository should be protected by an entitlement
  certificate.
* **images** *(array)* - an array of objects describing each image/layer in the repository

  * **id** *(str)* - the image id for the image

* **tags** *(obj)* - an object containing key, value paris of "tag-name":"image-id"

Example Redirect File Contents::

 {
  "type":"pulp-docker-redirect",
  "version":1,
  "repository":"docker",
  "repo-registry-id":"redhat/docker",
  "url":"http://www.foo.com/docker",
  "protected": true,
  "images":[
    {"id":"48e5f45168b97799ad0aafb7e2fef9fac57b5f16f6db7f67ba2000eb947637eb"},
    {"id":"511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158"},
    {"id":"769b9341d937a3dba9e460f664b4f183a6cecdd62b337220a28b3deb50ee0a02"},
    {"id":"bf747efa0e2fa9f7c691588ce3938944c75607a7bb5e757f7369f86904d97c78"}
    ],
  "tags": {"latest": "769b9341d937a3dba9e460f664b4f183a6cecdd62b337220a28b3deb50ee0a02"}
 }


