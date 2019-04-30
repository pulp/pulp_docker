Configuration
=============

Importer Configuration
----------------------

The Docker importer is configured by editing
``/etc/pulp/server/plugins.conf.d/docker_importer.json``. This file must be valid `JSON`_.

.. _JSON: http://json.org/

The importer supports the settings documented in Pulp's `importer config docs`_.

.. _importer config docs: https://docs.pulpproject.org/en/latest/user-guide/server.html#importers

The following docker specific properties are supported:

``enable_v1``
  Enables the docker v1 protocol. Defaults to False when not specified. DEPRECATED.

``enable_v2``
  Enables the docker v2 protocol. Defaults to True when not specified.

``tags``
  A CSV whitelist of tags to sync. If not provided, the importer will sync all available tags.
  This is only available for v2 content.
