#!/usr/bin/env python3

from setuptools import setup, find_packages

requirements = [
    'pulp-docker-common'
]

setup(
    name='pulp-docker-cli',
    version='3.0.0a1.dev0',
    packages=find_packages(exclude=['test']),
    url='http://www.pulpproject.org',
    install_requires=requirements,
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='pulp-cli extensions for docker image support',
    entry_points={
        'pulp.extensions.admin': [
            'repo_admin = pulp_docker.extensions.admin.pulp_cli:initialize',
        ]
    }
)
