Installation
============

.. _Pulp User Guide: https://docs.pulpproject.org

Prerequisites
-------------

pulp-docker 2.0 requires at least Pulp 2.8.

The only other requirement is to meet the prerequisites of the Pulp Platform.
Please see the `Pulp User Guide`_ for prerequisites including repository setup.


Server
------

::

    $ sudo yum install pulp-docker-plugins

Then run ``pulp-manage-db`` to initialize the new type in Pulp's database.

::

    $ sudo -u apache pulp-manage-db


Then restart each pulp component, as documented in the `Pulp User Guide`_.

Admin Client
------------

::

    $ sudo yum install pulp-docker-admin-extensions
