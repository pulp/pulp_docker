from setuptools import setup, find_packages

setup(
    name='pulp_docker_common',
    version='1.0.0c3',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='common code for pulp\'s docker image support',
)
