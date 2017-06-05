#!/usr/bin/env python3

from setuptools import setup, find_packages

requirements = [
    'pulpcore-plugin',
    'pulp-docker-common'
]

setup(
    name='pulp-docker',
    version='3.0.0a1.dev0',
    packages=find_packages(exclude=['test']),
    url='http://www.pulpproject.org',
    install_requires=requirements,
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='Plugin to enable docker image support in Pulp',
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
            'docker_tag=pulp_docker.plugins.models:Tag'
        ]
    }
)
