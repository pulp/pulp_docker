Distributor Configuration
=========================


Web Distributor
---------------

Type ID: ``docker_distributor``

The global configuration file for the docker_web_distributor plugin
can be found in ``/etc/pulp/server/plugin.conf.d/docker_distributor.json``.

All values from the global configuration can be overridden on the local config.

Supported keys
^^^^^^^^^^^^^^

``docker_publish_directory``
 The publish directory used for this distributor.  The web server should be configured to serve
  <publish_directory>/web.  The default value is ``/var/lib/pulp/published/docker``.

``redirect-url``
 The server URL that will be used when generating the redirect map for connecting the docker
 API to the location the content is stored. The value defaults to
 ``https://<server_name_from_pulp_server.conf>/pulp/docker/<repo_name>``.

``protected``
if "true" requests for this repo will be checked for an entitlement certificate authorizing
the server url for this repository; if "false" no authorization checking will be done.

Redirect File
^^^^^^^^^^^^^
The Web Distributor generates a json file with the details of the repository contents.
By default the file is published in ``/var/lib/pulp/published/docker/app/<reponame>.json``

The file has the following keys* **_href** *(string)* - uri path to retrieve this task report object.
* **type** (string)* - the type of the file.  This will always be "pulp-docker-redirect"
* **version** *(string)* - version of the format for the file.  Currently version 1
* **repository** *(string)* - the name of the repository this file is describing
* **data** *(array)* - an array of objects, one for each image in the repository
* * **id** *(str)* - the image id for the image
* * **url** *(str)* - the url where the image is located
* * **tag** *(str)* - a tag associated with this image.  This field is optional

Example Redirect File Contents::

 {
  "type":"pulp-docker-redirect",
  "version":1,
  "repository":"docker",
  "data":[
    {
      "url": "http://www.foo.com/48e5f45168b97799ad0aafb7e2fef9fac57b5f16f6db7f67ba2000eb947637eb/",
      "id": "48e5f45168b97799ad0aafb7e2fef9fac57b5f16f6db7f67ba2000eb947637eb"
    },{
      "url": "http://www.foo.com/511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158/",
      "id": "511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158"
    },{
      "url": "http://www.foo.com/769b9341d937a3dba9e460f664b4f183a6cecdd62b337220a28b3deb50ee0a02/",
      "tag": "latest",
      "id": "769b9341d937a3dba9e460f664b4f183a6cecdd62b337220a28b3deb50ee0a02"
    },{
      "url": "http://www.foo.com/bf747efa0e2fa9f7c691588ce3938944c75607a7bb5e757f7369f86904d97c78/",
      "id": "bf747efa0e2fa9f7c691588ce3938944c75607a7bb5e757f7369f86904d97c78"
    }
    ]
 }


