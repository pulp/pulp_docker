BLOB_TYPE_ID = 'docker_blob'
IMAGE_TYPE_ID = 'docker_image'
MANIFEST_TYPE_ID = 'docker_manifest'
MANIFEST_LIST_TYPE_ID = 'docker_manifest_list'
MANIFEST_LIST_TYPE = 'list'
MANIFEST_IMAGE_TYPE = 'image'
TAG_TYPE_ID = 'docker_tag'
IMPORTER_TYPE_ID = 'docker_importer'
IMPORTER_CONFIG_FILE_NAME = 'server/plugins.conf.d/docker_importer.json'
DISTRIBUTOR_WEB_TYPE_ID = 'docker_distributor_web'
DISTRIBUTOR_EXPORT_TYPE_ID = 'docker_distributor_export'
CLI_WEB_DISTRIBUTOR_ID = 'docker_web_distributor_name_cli'
CLI_EXPORT_DISTRIBUTOR_ID = 'docker_export_distributor_name_cli'
DISTRIBUTOR_CONFIG_FILE_NAME = 'server/plugins.conf.d/docker_distributor.json'
DISTRIBUTOR_EXPORT_CONFIG_FILE_NAME = 'server/plugins.conf.d/docker_distributor_export.json'
FOREIGN_LAYER = 'application/vnd.docker.image.rootfs.foreign.diff.tar.gzip'

REPO_NOTE_DOCKER = 'docker-repo'

# Config keys for the importer
CONFIG_KEY_UPSTREAM_NAME = 'upstream_name'

# Config keys for the distributor plugin conf
CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY = 'docker_publish_directory'
CONFIG_VALUE_DOCKER_PUBLISH_DIRECTORY = '/var/lib/pulp/published/docker'
CONFIG_KEY_EXPORT_FILE = 'export_file'

# Config keys for a distributor instance in the database
CONFIG_KEY_REDIRECT_URL = 'redirect-url'
CONFIG_KEY_PROTECTED = 'protected'
CONFIG_KEY_REPO_REGISTRY_ID = 'repo-registry-id'

# Config keys for an importer override config
CONFIG_KEY_MASK_ID = 'mask_id'
CONFIG_KEY_ENABLE_V1 = 'enable_v1'
CONFIG_KEY_ENABLE_V2 = 'enable_v2'
CONFIG_KEY_WHITELIST_TAGS = 'tags'

SYNC_STEP_MAIN = 'sync_step_main'
SYNC_STEP_METADATA = 'sync_step_metadata'
SYNC_STEP_DOWNLOAD = 'sync_step_download'
SYNC_STEP_SAVE = 'sync_step_save'
SYNC_STEP_SAVE_V1 = 'v1_sync_step_save'
SYNC_STEP_METADATA_V1 = 'v1_sync_step_metadata'
SYNC_STEP_GET_LOCAL_V1 = 'v1_sync_step_get_local'
SYNC_STEP_DOWNLOAD_V1 = 'v1_sync_step_download'

UPLOAD_STEP = 'upload_units_step'
UPLOAD_STEP_METADATA = 'upload_step_metadata'
UPLOAD_STEP_SAVE = 'upload_step_save'
UPLOAD_TAG_STEP = 'upload_tags_step'
UPLOAD_STEP_IMAGE_MANIFEST = 'upload_step_image_manifest'
UPLOAD_STEP_MANIFEST_LIST = 'upload_step_manifest_list'

# Keys that are specified on the repo config
PUBLISH_STEP_WEB_PUBLISHER = 'publish_to_web'
PUBLISH_STEP_EXPORT_PUBLISHER = 'export_to_tar'
PUBLISH_STEP_BLOBS = 'publish_blobs'
PUBLISH_STEP_IMAGES = 'publish_images'
PUBLISH_STEP_MANIFESTS = 'publish_manifests'
PUBLISH_STEP_MANIFEST_LISTS = 'publish_manifest_lists'
PUBLISH_STEP_REDIRECT_FILE = 'publish_redirect_file'
PUBLISH_STEP_TAGS = 'publish_tags'
PUBLISH_STEP_OVER_HTTP = 'publish_images_over_http'
PUBLISH_STEP_DIRECTORY = 'publish_directory'
PUBLISH_STEP_TAR = 'save_tar'

# Dictionary keys to be used when storing or accessing a list of tag dictionaries
# on the repo scratchpad
IMAGE_TAG_KEY = 'tag'
IMAGE_ID_KEY = 'image_id'

MEDIATYPE_MANIFEST_LIST = 'application/vnd.docker.distribution.manifest.list.v2+json'
MEDIATYPE_MANIFEST_S1 = 'application/vnd.docker.distribution.manifest.v1+json'
MEDIATYPE_MANIFEST_S2 = 'application/vnd.docker.distribution.manifest.v2+json'
MEDIATYPE_SIGNED_MANIFEST_S1 = 'application/vnd.docker.distribution.manifest.v1+prettyjws'

SUPPORTED_TYPES = (IMAGE_TYPE_ID, BLOB_TYPE_ID, MANIFEST_TYPE_ID, TAG_TYPE_ID)
