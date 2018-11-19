from setuptools import setup, find_packages


setup(
    name='pulp_docker_common',
    version='3.2.2b1',
    packages=find_packages(exclude=['test']),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='common code for pulp\'s docker image support',
)
