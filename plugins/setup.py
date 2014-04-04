from setuptools import setup, find_packages

setup(
    name='pulp_docker_plugins',
    version='0.1.0',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='plugins for docker image support in pulp',
    entry_points = {
        'pulp.importers': [
            'importer = pulp_docker.plugins.importers.importer:entry_point',
            'distributor = pulp_docker.plugins.distributors.distributor:entry_point',
        ]
    }
)
