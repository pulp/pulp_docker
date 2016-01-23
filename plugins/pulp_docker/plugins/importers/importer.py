from gettext import gettext as _
import logging
import shutil
import tempfile

from pulp.common.config import read_json_config
from pulp.plugins.importer import Importer
from pulp.server.db.model.criteria import UnitAssociationCriteria
import pulp.server.managers.factory as manager_factory

from pulp_docker.common import constants, tarutils
from pulp_docker.common.models import Image, Manifest, Blob
from pulp_docker.plugins.importers import sync, upload


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
            'types': [Image.TYPE_ID, Manifest.TYPE_ID, Blob.TYPE_ID]
        }

    def sync_repo(self, repo, sync_conduit, config):
        """
        Synchronizes content into the given repository. This call is responsible
        for adding new content units to Pulp as well as associating them to the
        given repository.

        While this call may be implemented using multiple threads, its execution
        from the Pulp server's standpoint should be synchronous. This call should
        not return until the sync is complete.

        It is not expected that this call be atomic. Should an error occur, it
        is not the responsibility of the importer to rollback any unit additions
        or associations that have been made.

        The returned report object is used to communicate the results of the
        sync back to the user. Care should be taken to i18n the free text "log"
        attribute in the report if applicable.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param sync_conduit: provides access to relevant Pulp functionality
        :type  sync_conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration

        :return: report of the details of the sync
        :rtype:  pulp.plugins.model.SyncReport
        """
        working_dir = tempfile.mkdtemp(dir=repo.working_dir)
        try:
            self.sync_step = sync.SyncStep(repo=repo, conduit=sync_conduit, config=config,
                                           working_dir=working_dir)
            return self.sync_step.sync()
        finally:
            shutil.rmtree(working_dir, ignore_errors=True)

    def cancel_sync_repo(self):
        """
        Cancels an in-progress sync.

        This call is responsible for halting a current sync by stopping any
        in-progress downloads and performing any cleanup necessary to get the
        system back into a stable state.
        """
        self.sync_step.cancel()

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
        mask_id = config.get(constants.CONFIG_KEY_MASK_ID)
        models = upload.get_models(metadata, mask_id)
        ancestry = tarutils.get_ancestry(models[0].image_id, metadata)
        # save those models as units in pulp
        upload.save_models(conduit, models, ancestry, file_path)
        upload.update_tags(repo.id, file_path)

    def import_units(self, source_repo, dest_repo, import_conduit, config, units=None):
        """
        Import content units into the given repository. This method will be
        called in a number of different situations:
         * A user is attempting to copy a content unit from one repository
           into the repository that uses this importer
         * A user is attempting to add an orphaned unit into a repository.

        This call has two options for handling the requested units:
         * Associate the given units with the destination repository. This will
           link the repository with the existing unit directly; changes to the
           unit will be reflected in all repositories that reference it.
         * Create a new unit and save it to the repository. This would act as
           a deep copy of sorts, creating a unique unit in the database. Keep
           in mind that the unit key must change in order for the unit to
           be considered different than the supplied one.

        The APIs for both approaches are similar to those in the sync conduit.
        In the case of a simple association, the init_unit step can be skipped
        and save_unit simply called on each specified unit.

        The units argument is optional. If None, all units in the source
        repository should be imported. The conduit is used to query for those
        units. If specified, only the units indicated should be imported (this
        is the case where the caller passed a filter to Pulp).

        :param source_repo: metadata describing the repository containing the
               units to import
        :type  source_repo: pulp.plugins.model.Repository

        :param dest_repo: metadata describing the repository to import units
               into
        :type  dest_repo: pulp.plugins.model.Repository

        :param import_conduit: provides access to relevant Pulp functionality
        :type  import_conduit: pulp.plugins.conduits.unit_import.ImportUnitConduit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration

        :param units: optional list of pre-filtered units to import
        :type  units: list of pulp.plugins.model.Unit

        :return: list of Unit instances that were saved to the destination repository
        :rtype:  list
        """
        units_added = []
        units_added.extend(DockerImporter._import_images(import_conduit, units))
        units_added.extend(DockerImporter._import_manifests(import_conduit, units))
        return units_added

    @staticmethod
    def _import_images(conduit, units):
        """
        Import images and referenced images.

        :param conduit: provides access to relevant Pulp functionality
        :type conduit: pulp.plugins.conduits.unit_import.ImportUnitConduit
        :param units: optional list of pre-filtered units to import
        :type  units: list of pulp.plugins.model.Unit
        :return: list of units that were copied to the destination repository
        :rtype:  list
        """
        # Determine which units are being copied
        if units is None:
            criteria = UnitAssociationCriteria(type_ids=[constants.IMAGE_TYPE_ID])
            units = conduit.get_source_units(criteria=criteria)

        # Associate to the new repository
        known_units = set()
        units_added = []

        while True:
            units_to_add = set()

            # Associate the units to the repository
            for u in units:
                if u.type_id != constants.IMAGE_TYPE_ID:
                    continue
                conduit.associate_unit(u)
                units_added.append(u)
                known_units.add(u.unit_key['image_id'])
                parent_id = u.metadata.get('parent_id')
                if parent_id:
                    units_to_add.add(parent_id)
            # Filter out units we have already added
            units_to_add.difference_update(known_units)
            # Find any new units to add to the repository
            if units_to_add:
                unit_filter = {'image_id': {'$in': list(units_to_add)}}
                criteria = UnitAssociationCriteria(type_ids=[constants.IMAGE_TYPE_ID],
                                                   unit_filters=unit_filter)
                units = conduit.get_source_units(criteria=criteria)
            else:
                # Break out of the loop since there were no units to add to the list
                break

        return units_added

    @staticmethod
    def _import_manifests(conduit, units):
        """
        Import manifests and referenced blobs.

        :param conduit: provides access to relevant Pulp functionality
        :type conduit: pulp.plugins.conduits.unit_import.ImportUnitConduit
        :param units: optional list of pre-filtered units to import
        :type  units: list of pulp.plugins.model.Unit
        :return: list of units that were copied to the destination repository
        :rtype:  list
        """
        units_added = []

        # All manifests if not specified

        if units is None:
            criteria = UnitAssociationCriteria(type_ids=[Manifest.TYPE_ID])
            units = conduit.get_source_units(criteria=criteria)

        # Add manifests and catalog referenced blobs

        blob_digests = set()
        for unit in units:
            if unit.type_id != Manifest.TYPE_ID:
                continue
            manifest = unit
            conduit.associate_unit(manifest)
            units_added.append(manifest)
            for layer in manifest.metadata['fs_layers']:
                digest = layer['blobSum']
                blob_digests.add(digest)

        # Add referenced blobs

        unit_filter = {
            'digest': {
                '$in': sorted(blob_digests)
            }
        }
        criteria = UnitAssociationCriteria(type_ids=[Blob.TYPE_ID], unit_filters=unit_filter)
        for blob in conduit.get_source_units(criteria=criteria):
            conduit.associate_unit(blob)
            units_added.append(blob)
        return units_added

    def validate_config(self, repo, config):
        """
        We don't have a config yet, so it's always valid
        """
        return True, ''

    def remove_units(self, repo, units, config):
        """
        Removes content units from the given repository.

        This method also removes the tags associated with images in the repository.

        This call will not result in the unit being deleted from Pulp itself.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param units: list of objects describing the units to import in
                      this call
        :type  units: list of pulp.plugins.model.AssociatedUnit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        self._purge_unreferenced_tags(repo, units)
        self._purge_orphaned_blobs(repo, units)

    @staticmethod
    def _purge_unreferenced_tags(repo, units):
        """
        Purge tags associated with images in the repository.

        :param repo: The affected repository.
        :type  repo: pulp.plugins.model.Repository
        :param units: List of removed units.
        :type  units: list of: pulp.plugins.model.AssociatedUnit
        """
        unit_ids = set()
        manager = manager_factory.repo_manager()
        scratchpad = manager.get_repo_scratchpad(repo.id)
        for unit in units:
            if unit.type_id != Image.TYPE_ID:
                continue
            unit_ids.add(unit.unit_key[u'image_id'])
        tags = scratchpad.get(u'tags', [])
        for tag in tags[:]:
            if tag[constants.IMAGE_ID_KEY] not in unit_ids:
                continue
            tags.remove(tag)
        scratchpad[u'tags'] = tags
        manager.set_repo_scratchpad(repo.id, scratchpad)

    @staticmethod
    def _purge_orphaned_blobs(repo, units):
        """
        Purge blobs associated with removed manifests when no longer
        referenced by any remaining manifests.

        :param repo: The affected repository.
        :type  repo: pulp.plugins.model.Repository
        :param units: List of removed units.
        :type  units: list of: pulp.plugins.model.AssociatedUnit
        """
        # Find blob digests referenced by removed manifests (orphaned)

        orphaned = set()
        for unit in units:
            if unit.type_id != Manifest.TYPE_ID:
                continue
            manifest = unit
            for layer in manifest.metadata['fs_layers']:
                digest = layer['blobSum']
                orphaned.add(digest)

        # Find blob digests still referenced by other manifests (adopted)

        if not orphaned:
            # nothing orphaned
            return
        adopted = set()
        manager = manager_factory.repo_unit_association_query_manager()
        for manifest in manager.get_units_by_type(repo.id, Manifest.TYPE_ID):
            for layer in manifest.metadata['fs_layers']:
                digest = layer['blobSum']
                adopted.add(digest)

        # Remove unreferenced blobs

        orphaned = orphaned.difference(adopted)
        if not orphaned:
            # all adopted
            return

        unit_filter = {
            'digest': {
                '$in': sorted(orphaned)
            }
        }
        criteria = UnitAssociationCriteria(
            type_ids=[Blob.TYPE_ID],
            unit_filters=unit_filter)
        manager = manager_factory.repo_unit_association_manager()
        manager.unassociate_by_criteria(
            repo_id=repo.id,
            criteria=criteria,
            owner_type='',  # unused
            owner_id='',    # unused
            notify_plugins=False)
