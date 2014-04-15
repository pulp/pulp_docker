IMAGE_TYPE_ID = 'docker_image'
IMPORTER_TYPE_ID = 'docker_importer'
IMPORTER_CONFIG_FILE_NAME = 'server/plugins.conf.d/docker_importer.json'
DISTRIBUTOR_TYPE_ID = 'docker_distributor'
CLI_WEB_DISTRIBUTOR_ID = 'docker_web_distributor'
DISTRIBUTOR_CONFIG_FILE_NAME = 'server/plugins.conf.d/docker_distributor.json'

REPO_NOTE_DOCKER = 'docker-repo'

# Config keys for the distributor plugin conf
CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY = 'docker_publish_directory'
CONFIG_VALUE_DOCKER_PUBLISH_DIRECTORY = '/var/lib/pulp/published/docker'

# Config keys for a distributor instance in the database
CONFIG_KEY_SERVER_URL = 'server-url'
CONFIG_KEY_PROTECTED = 'protected'

#Keys that are specified on the repo config
REPO_CONFIG_KEY_REPO_RELATIVE_DIRECTORY = 'repo_relative_directory'

PUBLISH_STEP_IMAGES = 'publish_images'
PUBLISH_STEP_OVER_HTTP = 'publish_images_over_http'
PUBLISH_STEP_DIRECTORY = 'publish_directory'
