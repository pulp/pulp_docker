IMAGE_TYPE_ID = 'docker_image'
IMPORTER_TYPE_ID = 'docker_importer'
IMPORTER_CONFIG_FILE_NAME = 'server/plugins.conf.d/docker_importer.json'
DISTRIBUTOR_TYPE_ID = 'docker_distributor'
DISTRIBUTOR_CONFIG_FILE_NAME = 'server/plugins.conf.d/docker_distributor.json'

# Config keys for the distributor plugin conf
CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY = 'DOCKER_PUBLISH_DIRECTORY'

# Config keys for a distributor instance in the database
CONFIG_KEY_RELATIVE_URL = 'relative_url'

#Keys that are specified on the repo config
REPO_CONFIG_KEY_REPO_RELATIVE_DIRECTORY = 'repo_relative_directory'

PUBLISH_STEP_IMAGES = 'publish_images'
PUBLISH_STEP_OVER_HTTP = 'publish_images_over_http'
PUBLISH_STEP_DIRECTORY = 'publish_directory'
