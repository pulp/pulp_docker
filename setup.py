#!/usr/bin/env python3

from setuptools import setup

requirements = [
    'pulpcore-plugin',
]

setup(
    name='pulp-docker',
    version='0.0.1a1.dev1',
    description='pulp-docker plugin for the Pulp Project',
    license='GPLv2+',
    python_requires='>=3.5',
    author='Pulp Project Developers',
    author_email='pulp-list@redhat.com',
    url='http://www.pulpproject.org',
    install_requires=requirements,
    include_package_data=True,
    packages=['pulp_docker', 'pulp_docker.app'],
    classifiers=(
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Framework :: Django',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ),
    entry_points={
        'pulpcore.plugin': [
            'pulp_docker = pulp_docker:default_app_config',
        ]
    }
)
