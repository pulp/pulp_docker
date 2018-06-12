Importer
========

ID: ``docker_importer``

Configuration
-------------

The following options are available to the docker importer configuration.

``enable_v1``
 Boolean to control whether to attempt using registry API v1 during
 synchronization. Default is False.

``enable_v2``
 Boolean to control whether to attempt using registry API v2 during
 synchronization. Default is True.

``tags``
 CSV whitelist of tags to include on sync. If not provided, sync will download
 all available tags. This feature is only available for v2 content.

.. note::
    Tags is only considered at sync time. If the list of tags is changed after,
    and a tag is not wanted anymore, a manual removal of that tag should occur.


``feed``
 The URL for the docker repository to import images from.

``mask_id``
 Supported only as an override config option to a repository upload command.
 When this option is used, the upload command will skip adding given image and
 any ancestors of that image to the repository. This is related only to the upload
 of v1 content.

``upstream_name``
 The name of the repository to import from the upstream repository.
