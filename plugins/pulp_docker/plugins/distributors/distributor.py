from gettext import gettext as _
import logging

from pulp.common.config import read_json_config
from pulp.plugins.distributor import Distributor

from pulp_docker.common import constants


_logger = logging.getLogger(__name__)


def entry_point():
    """
    Entry point that pulp platform uses to load the distributor
    :return: distributor class and its config
    :rtype:  Distributor, dict
    """
    plugin_config = read_json_config(constants.DISTRIBUTOR_CONFIG_FILE_NAME)
    return DockerDistributor, plugin_config


class DockerDistributor(Distributor):
    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this distributor. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this distributor. Must be unique
          across all distributors. Only letters and underscores are valid.
        * display_name - User-friendly identification of the distributor.
        * types - List of all content type IDs that may be published using this
          distributor.

        :return:    keys and values listed above
        :rtype:     dict
        """
        return {
            'id': constants.DISTRIBUTOR_TYPE_ID,
            'display_name': _('Docker Distributor'),
            'types': [constants.IMAGE_TYPE_ID]
        }
