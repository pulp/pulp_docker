#!/usr/bin/env python2

from setuptools import setup, find_packages


setup(
    name='pulp_docker_extensions_admin',
    version='2.0.0b7',
    packages=find_packages(exclude=['test']),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='pulp-admin extensions for docker image support',
    entry_points={
        'pulp.extensions.admin': [
            'repo_admin = pulp_docker.extensions.admin.pulp_cli:initialize',
        ]
    }
)
