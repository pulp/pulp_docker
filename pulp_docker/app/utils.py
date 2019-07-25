def _convert_manifest(tag, accepted_media_types):
    if tag.tagged_manifest.media_type == MEDIA_TYPE.MANIFEST_V2:
        # convert schema2 to schema1
        schema1_builder = Schema1ManifestBuilder(tag.name)
        _populate_schema1_builder(schema1_builder, tag.tagged_manifest)
        schema1_converted, digest = schema1_builder.build()
        return schema1_builder, True, digest
    elif tag.tagged_manifest.media_type == MEDIA_TYPE.MANIFEST_LIST:
        legacy = _get_legacy_manifest(tag)
        if legacy is None:
            return None, None, None
        if legacy.media_type == MEDIA_TYPE.MANIFEST_V2 and legacy.media_type not in accepted_media_types:
            # convert schema2 to schema1
            schema1_builder = Schema1ManifestBuilder(tag.name)
            self._populate_schema1_builder(schema1_builder, legacy)
            schema1_converted, digest = schema1_builder.build()
            return schema1_converted, True, digest
        else:
            # return legacy without conversion
            return legacy, False, legacy.digest


def _get_legacy_manifest(tag):
    ml = tag.tagged_manifest.manifests
    for manifest in ml.image_manifests:
        architecture = manifest['architecture']
        os = manifest['os']
        if architecture != 'amd64' or os != 'linux':
            continue
        # return manifest.manifest_list
        return manifest.image_manifest
    return None


def _populate_schema1_builder(schema1_builder, manifest):
    """
    Populates a Schema1ManifestBuilder with the layers and config
    """
    schema2_config = _get_config(manifest)
    layers = list(_manifest_image_layers(schema2_config))


def _get_config(manifest):
    config_blob = manifest.config_blob
    return DockerSchema2Config(config_blob)


def _manifest_image_layers(config):
    return DockerV2ManifestImageLayer(config)


class Schema1ManifestBuilder(object):
  """
  Abstraction around creating new Schema1Manifests.
  """

    def __init__(self, tag):

    def build():
        """
        build schema1 + signature
        """
