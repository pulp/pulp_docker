from setuptools import setup, find_packages

setup(
    name='pulp_docker_common',
    version='2.0.0b5',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='common code for pulp\'s docker image support',
)
