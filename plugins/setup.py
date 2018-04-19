#!/usr/bin/env python2

from setuptools import setup, find_packages


setup(
    name='pulp_docker_plugins',
    version='3.1.3b1',
    packages=find_packages(exclude=['test', 'test.*']),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='plugins for docker image support in pulp',
    entry_points={
        'pulp.importers': [
            'importer = pulp_docker.plugins.importers.importer:entry_point',
        ],
        'pulp.distributors': [
            'web_distributor = pulp_docker.plugins.distributors.distributor_web:entry_point',
            'export_distributor = pulp_docker.plugins.distributors.distributor_export:entry_point',
            'rsync_distributor = pulp_docker.plugins.distributors.rsync_distributor:entry_point'
        ],
        'pulp.server.db.migrations': [
            'pulp_docker = pulp_docker.plugins.migrations'
        ],
        'pulp.unit_models': [
            'docker_blob=pulp_docker.plugins.models:Blob',
            'docker_image=pulp_docker.plugins.models:Image',
            'docker_manifest=pulp_docker.plugins.models:Manifest',
            'docker_manifest_list=pulp_docker.plugins.models:ManifestList',
            'docker_tag=pulp_docker.plugins.models:Tag'
        ]
    }
)
