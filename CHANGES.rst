=========
Changelog
=========

..
    You should *NOT* be adding new change log entries to this file, this
    file is managed by towncrier. You *may* edit previous change logs to
    fix problems like typo corrections or such.
    To add a new change log entry, please see
    https://docs.pulpproject.org/en/3.0/nightly/contributing/git.html#changelog-update

    WARNING: Don't drop the next directive!

.. towncrier release notes start

4.0.0b7 (2019-10-02)
====================


Bugfixes
--------

- Fix a bug that allowed arbitrary url prefixes for custom endpoints.
  `#5486 <https://pulp.plan.io/issues/5486>`_
- Add Docker-Distribution-API-Version header among response headers.
  `#5527 <https://pulp.plan.io/issues/5527>`_


Misc
----

- `#5470 <https://pulp.plan.io/issues/5470>`_


----


4.0.0b6 (2019-09-05)
====================


Features
--------

- Add endpoint to recursively copy manifests from a source repository to a destination repository.
  `#3403 <https://pulp.plan.io/issues/3403>`_
- Add endpoint to recursively add docker content to a repository.
  `#3405 <https://pulp.plan.io/issues/3405>`_
- As a user I can sync from a docker repo published by Pulp2/Pulp3.
  `#4737 <https://pulp.plan.io/issues/4737>`_
- Add support for tagging and untagging manifests via an additional endpoint
  `#4934 <https://pulp.plan.io/issues/4934>`_
- Add endpoint for copying all tags from a source repository, or specific tags by name.
  `#4947 <https://pulp.plan.io/issues/4947>`_
- Add ability to filter Manifests and ManifestTags by media_type and digest
  `#5033 <https://pulp.plan.io/issues/5033>`_
- Add ability to filter Manifests, ManifestTags and Blobs by multiple media_types
  `#5157 <https://pulp.plan.io/issues/5157>`_
- Add endpoint to recursively remove docker content from a repository.
  `#5179 <https://pulp.plan.io/issues/5179>`_


Bugfixes
--------

- Allow Accept header to send multiple values.
  `#5211 <https://pulp.plan.io/issues/5211>`_
- Populate ManifestListManifest thru table during sync.
  `#5235 <https://pulp.plan.io/issues/5235>`_
- Fixed a problem where repeated syncs created invalid orphaned tags.
  `#5252 <https://pulp.plan.io/issues/5252>`_


Misc
----

- `#4681 <https://pulp.plan.io/issues/4681>`_, `#5213 <https://pulp.plan.io/issues/5213>`_, `#5218 <https://pulp.plan.io/issues/5218>`_


----


4.0.0b5 (2019-07-04)
====================


Bugfixes
--------

- Add 'Docker-Content-Digest' header to the response headers.
  `#4646 <https://pulp.plan.io/issues/4646>`_
- Allow docker remote whitelist_tags to be unset to null.
  `#5017 <https://pulp.plan.io/issues/5017>`_
- Remove schema1 manifest signature when calculating its digest.
  `#5037 <https://pulp.plan.io/issues/5037>`_


Improved Documentation
----------------------

- Switch to using `towncrier <https://github.com/hawkowl/towncrier>`_ for better release notes.
  `#4875 <https://pulp.plan.io/issues/4875>`_
- Add an example to the whitelist_tag help text
  `#4994 <https://pulp.plan.io/issues/4994>`_
- Add list of features to the docker landing page.
  `#5030 <https://pulp.plan.io/issues/5030>`_


Misc
----

- `#4572 <https://pulp.plan.io/issues/4572>`_, `#4994 <https://pulp.plan.io/issues/4994>`_, `#5014 <https://pulp.plan.io/issues/5014>`_


----
