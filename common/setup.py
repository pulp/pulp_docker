from setuptools import setup, find_packages


setup(
    name='pulp_docker_common',
    version='3.2a1',
    packages=find_packages(exclude=['test']),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='Common code for Pulp\'s docker image support',
)
