pulp_docker
===========

Allow Pulp to manage Docker images.  Not to be confused with a Docker image running Pulp whish may be found in the [Packaging repo](https://github.com/pulp/packaging/tree/docker).

tagging
-------

To tag a new version, edit pulp-docker.spec to the new version, create a PR,
and once merged run `tito tag --keep-version`. Do not use the tito
auto-increment tagger for the time being.

