from setuptools import setup, find_packages

setup(
    name='pulp_docker_plugins',
    version='1.0.0b2',
    packages=find_packages(),
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
        ]
    }
)
