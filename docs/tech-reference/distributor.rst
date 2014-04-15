Distributor Configuration
=========================


Web Distributor
---------------

Type ID: ``docker_distributor``

The global configuration file for the docker_web_distributor plugin
can be found in ``/etc/pulp/server/plugin.conf.d/docker_distributor.json``.

Local all values from the global configuration can be overridden on the local config.

Supported keys

``docker_publish_directory``
 The publish directory used for this distributor.  The web server should be configured to serve
  <publish_directory>/web.  The default value is ``/var/lib/pulp/published/docker``.

``server-url``
 The server URL that will be used when generating the redirect map for connecting the docker
 API to the location the content is stored. The value defaults to
 ``https://<server_name_from_pulp_server.conf>/pulp/docker/<repo_name>``.

``protected``
if "true" requests for this repo will be checked for an entitlement certificate authorizing
the server url for this repository; if "false" no authorization checking will be done.