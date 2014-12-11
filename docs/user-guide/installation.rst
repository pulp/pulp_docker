Installation
============

.. _Pulp User Guide: http://pulp-user-guide.readthedocs.org

Prerequisites
-------------

The only requirement is to meet the prerequisites of the Pulp Platform. Please
see the `Pulp User Guide`_ for prerequisites including repository setup.

.. note::

   If you are installing on Fedora, you will need to install ``docker-io`` instead
   of ``docker``. See the official `Docker Documentation`_ for more information.

.. _Docker Documentation: https://docs.docker.com/

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

