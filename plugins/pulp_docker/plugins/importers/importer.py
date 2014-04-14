from gettext import gettext as _
import logging

from pulp.common.config import read_json_config
from pulp.plugins.importer import Importer

from pulp_docker.common import constants, tarutils
from pulp_docker.plugins.importers import upload


_logger = logging.getLogger(__name__)


def entry_point():
    """
    Entry point that pulp platform uses to load the importer
    :return: importer class and its config
    :rtype:  Importer, dict
    """
    plugin_config = read_json_config(constants.IMPORTER_CONFIG_FILE_NAME)
    return DockerImporter, plugin_config


class DockerImporter(Importer):
    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this importer. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this importer. Must be unique
          across all importers. Only letters and underscores are valid.
        * display_name - User-friendly identification of the importer.
        * types - List of all content type IDs that may be imported using this
          importer.

        :return:    keys and values listed above
        :rtype:     dict
        """
        return {
            'id': constants.IMPORTER_TYPE_ID,
            'display_name': _('Docker Importer'),
            'types': [constants.IMAGE_TYPE_ID]
        }

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        """
        Upload a docker image. The file should be the product of "docker save".
        This will import all images in that tarfile into the specified
        repository, each as an individual unit. This will also update the
        repo's tags to reflect the tags present in the tarfile.

        The following is copied from the superclass.

        :param repo:      metadata describing the repository
        :type  repo:      pulp.plugins.model.Repository
        :param type_id:   type of unit being uploaded
        :type  type_id:   str
        :param unit_key:  identifier for the unit, specified by the user
        :type  unit_key:  dict
        :param metadata:  any user-specified metadata for the unit
        :type  metadata:  dict
        :param file_path: path on the Pulp server's filesystem to the temporary location of the
                          uploaded file; may be None in the event that a unit is comprised entirely
                          of metadata and has no bits associated
        :type  file_path: str
        :param conduit:   provides access to relevant Pulp functionality
        :type  conduit:   pulp.plugins.conduits.unit_add.UnitAddConduit
        :param config:    plugin configuration for the repository
        :type  config:    pulp.plugins.config.PluginCallConfiguration
        :return:          A dictionary describing the success or failure of the upload. It must
                          contain the following keys:
                            'success_flag': bool. Indicates whether the upload was successful
                            'summary':      json-serializable object, providing summary
                            'details':      json-serializable object, providing details
        :rtype:           dict
        """
        # retrieve metadata from the tarball
        metadata = tarutils.get_metadata(file_path)
        # turn that metadata into a collection of models
        models = upload.get_models(metadata, unit_key)
        ancestry = tarutils.get_ancestry(models[0].image_id, metadata)
        # save those models as units in pulp
        upload.save_models(conduit, models, ancestry, file_path)
        upload.update_tags(repo.id, file_path)

    def validate_config(self, repo, config):
        """
        We don't have a config yet, so it's always valid
        """
        return True, ''
