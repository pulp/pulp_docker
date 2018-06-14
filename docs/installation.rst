User Setup
==========

Install pulp-docker
-------------------

This document assumes that you have
`installed pulpcore <https://docs.pulpproject.org/en/3.0/nightly/installation/instructions.html>`_
into a the virtual environment ``pulpvenv``.

Users should install from **either** PyPI or source.

From PyPI
*********

From Source
***********

.. code-block:: bash

   source /path/to/pulpvenv/bin/activate
   git clone https://github.com/pulp/pulp_docker.git
   cd pulp_docker
   pip install -e .

Make and Run Migrations
-----------------------

.. code-block:: bash

   pulp-manager makemigrations pulp_docker
   pulp-manager migrate pulp_docker

Run Services
------------

.. code-block:: bash

   pulp-manager runserver
   sudo systemctl restart pulp_resource_manager
   sudo systemctl restart pulp_worker@1
   sudo systemctl restart pulp_worker@2
