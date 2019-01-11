#!/usr/bin/env python3

from setuptools import find_packages, setup

requirements = [
    'pulpcore-plugin>=0.1.0b16',
]

setup(
    name='pulp-docker',
    version='4.0a1.dev1',
    description='pulp-docker plugin for the Pulp Project',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    url='http://pulpproject.org/',
    python_requires='>=3.6',
    install_requires=requirements,
    include_package_data=True,
    packages=find_packages(exclude=['tests', 'tests.*']),
    classifiers=(
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Framework :: Django',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ),
    entry_points={
        'pulpcore.plugin': [
            'pulp_docker = pulp_docker:default_app_config',
        ]
    }
)
