from gettext import gettext as _
import logging

from pulp.common.config import read_json_config
from pulp.plugins.importer import Importer
from pulp.server.controllers import repository
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.managers.repo import unit_association
import pulp.server.managers.factory as manager_factory
from pulp.server.exceptions import PulpCodedValidationException

from pulp_docker.common import constants
from pulp_docker.plugins import models
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
            'types': [constants.BLOB_TYPE_ID, constants.IMAGE_TYPE_ID, constants.MANIFEST_TYPE_ID,
                      constants.MANIFEST_LIST_TYPE_ID, constants.TAG_TYPE_ID]
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
        self.sync_step = sync.SyncStep(repo=repo, conduit=sync_conduit, config=config)

        return self.sync_step.process_lifecycle()

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
        Upload a Docker Image. The file should be the product of "docker save".
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
        try:
            upload_step = upload.UploadStep(repo=repo, file_path=file_path, config=config,
                                            metadata=metadata, type_id=type_id)
            upload_step.process_lifecycle()
        except PulpCodedValidationException:
            raise
        except Exception as e:
            return {'success_flag': False, 'summary': e.message, 'details': {}}
        details = {}
        if upload_step.uploaded_unit:
            unit = upload_step.uploaded_unit
            details.update(unit=dict(type_id=unit.type_id,
                                     unit_key=unit.unit_key,
                                     metadata=self._get_unit_metadata(unit)))
        return {'success_flag': True, 'summary': '', 'details': details}

    @classmethod
    def _get_unit_metadata(cls, unit):
        ret = dict()
        for k in unit.__class__._fields:
            if k.startswith('_'):
                continue
            ret[k] = getattr(unit, k)
        return ret

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
        if units is None:
            criteria = UnitAssociationCriteria(
                type_ids=[constants.IMAGE_TYPE_ID, constants.TAG_TYPE_ID,
                          constants.MANIFEST_TYPE_ID, constants.MANIFEST_LIST_TYPE_ID,
                          constants.BLOB_TYPE_ID])
            units = import_conduit.get_source_units(criteria=criteria)

        unit_importers = {
            models.Image: DockerImporter._import_image,
            models.Tag: DockerImporter._import_tag,
            models.Manifest: DockerImporter._import_manifest,
            models.ManifestList: DockerImporter._import_manifest_list,
            models.Blob: DockerImporter._import_blob
        }

        units_added = set()
        for unit in units:
            units_added |= set(unit_importers[type(unit)](import_conduit, unit, dest_repo.repo_obj))

        return list(units_added)

    @staticmethod
    def _import_image(conduit, unit, dest_repo):
        """
        Import the Image and the Images it references.

        :param conduit:   provides access to relevant Pulp functionality
        :type  conduit:   pulp.plugins.conduits.unit_import.ImportUnitConduit
        :param unit:      The Image to import
        :type  unit:      pulp_docker.plugins.models.Image
        :param dest_repo: The destination repository that the Manifest is being imported to.
        :type  dest_repo: pulp.server.db.model.Repository
        :return:          set of Images that were copied to the destination repository
        :rtype:           set
        """
        # Associate to the new repository
        known_units = set()
        units_added = set()
        # The loop below expects a list of units as it recurses
        units = [unit]

        while True:
            units_to_add = set()

            # Associate the units to the repository
            for u in units:
                repository.associate_single_unit(dest_repo, u)
                units_added.add(u)
                known_units.add(u.unit_key['image_id'])
                parent_id = u.parent_id
                if parent_id:
                    units_to_add.add(parent_id)
            # Filter out units we have already added
            units_to_add.difference_update(known_units)
            # Find any new units to add to the repository
            if units_to_add:
                units = models.Image.objects.filter(image_id__in=list(units_to_add))
            else:
                # Break out of the loop since there were no units to add to the list
                break

        return list(units_added)

    @staticmethod
    def _import_tag(conduit, unit, dest_repo):
        """
        Import a Tag, and the Manifests(image manifests and manifest lists) and Blobs it references.

        :param conduit:   provides access to relevant Pulp functionality
        :type  conduit:   pulp.plugins.conduits.unit_import.ImportUnitConduit
        :param unit:      The Tag to be imported to the repository
        :type  unit:      pulp_docker.plugins.models.Tag
        :param dest_repo: The destination repository that the Tag is being imported to. This is
                          needed because technically we are creating a copy of the Tag there rather
                          than an association of the Tag, and the repo_id is a required field on the
                          Tag object.
        :type  dest_repo: pulp.server.db.model.Repository
        :return:          list of Units that were copied to the destination repository
        :rtype:           list
        """
        units_added = set()

        # We need to create a copy of the Tag with the destination repository's id, but other fields
        # copied from the source Tag.
        manifest_digests_to_import = set()
        tag = models.Tag.objects.tag_manifest(repo_id=dest_repo.repo_id, tag_name=unit.name,
                                              manifest_digest=unit.manifest_digest,
                                              schema_version=unit.schema_version,
                                              manifest_type=unit.manifest_type,
                                              pulp_user_metadata=unit.pulp_user_metadata)
        units_added.add(tag)
        conduit.associate_unit(tag)
        manifest_digests_to_import.add(unit.manifest_digest)

        if tag.manifest_type == constants.MANIFEST_LIST_TYPE:
            # Add referenced manifest lists
            for manifest in models.ManifestList.objects.filter(
                    digest__in=sorted(manifest_digests_to_import)):
                units_added |= set(DockerImporter._import_manifest_list(
                                   conduit, manifest, dest_repo))
        else:
            # Add referenced manifests
            for manifest in models.Manifest.objects.filter(
                    digest__in=sorted(manifest_digests_to_import)):
                units_added |= set(DockerImporter._import_manifest(conduit, manifest, dest_repo))

        return list(units_added)

    @staticmethod
    def _import_manifest(conduit, unit, dest_repo):
        """
        Import a Manifest and its referenced Blobs.

        :param conduit:   provides access to relevant Pulp functionality
        :type  conduit:   pulp.plugins.conduits.unit_import.ImportUnitConduit
        :param unit:      The Manifest to import
        :type  unit:      pulp_docker.plugins.Model.Manifest
        :param dest_repo: The destination repository that the Manifest is being imported to.
        :type  dest_repo: pulp.server.db.model.Repository
        :return:          list of Units that were copied to the destination repository
        :rtype:           list
        """
        units_added = set()

        # Collect referenced blobs
        blob_digests = set()
        for layer in unit.fs_layers:
            blob_digests.add(layer.blob_sum)

        # in manifest schema version 2 there is an additional blob layer called config_layer
        if unit.config_layer:
            blob_digests.add(unit.config_layer)

        # Add referenced blobs
        for blob in models.Blob.objects.filter(digest__in=sorted(blob_digests)):
            units_added |= set(DockerImporter._import_blob(conduit, blob, dest_repo))

        # Add manifests
        repository.associate_single_unit(dest_repo, unit)
        units_added.add(unit)

        return units_added

    @staticmethod
    def _import_manifest_list(conduit, unit, dest_repo):
        """
        Import a Manifest List and its referenced image manifests.

        :param conduit:   provides access to relevant Pulp functionality
        :type  conduit:   pulp.plugins.conduits.unit_import.ImportUnitConduit
        :param unit:      The Manifest List to import
        :type  unit:      pulp_docker.plugins.Model.ManifestList
        :param dest_repo: The destination repository that the ManifestList is being imported to.
        :type  dest_repo: pulp.server.db.model.Repository
        :return:          list of Units that were copied to the destination repository
        :rtype:           list
        """

        units_added = set()

        # Collect referenced manifests
        manifest_digests = set()
        for manifest in unit.manifests:
            manifest_digests.add(manifest.digest)

        if unit.amd64_digest:
            manifest_digests.add(unit.amd64_digest)

        # Add referenced manifests
        for manifest in models.Manifest.objects.filter(digest__in=sorted(manifest_digests)):
            units_added |= set(DockerImporter._import_manifest(conduit, manifest, dest_repo))

        # Add manifest lists
        repository.associate_single_unit(dest_repo, unit)
        units_added.add(unit)

        return units_added

    @staticmethod
    def _import_blob(conduit, unit, dest_repo):
        """
        Import a Blob.

        :param conduit:   provides access to relevant Pulp functionality
        :type  conduit:   pulp.plugins.conduits.unit_import.ImportUnitConduit
        :param unit:      The Blob to import
        :type  unit:      pulp_docker.plugins.Model.Blob
        :param dest_repo: The destination repository that the Blob is being imported to.
        :type  dest_repo: pulp.server.db.model.Repository
        :return:          list containing the Blob that was copied to the destination repository
        :rtype:           list
        """
        repository.associate_single_unit(dest_repo, unit)
        return [unit]

    def validate_config(self, repo, config):
        """
        We don't have a config yet, so it's always valid
        """
        return True, ''

    def remove_units(self, repo, units, config):
        """
        Removes content units from the given repository.

        This method also removes tags associated with Images, Tags associated with Manifests,
        unreferenced Blobs associated with Image Manifests, unreferenced Image Manifests
        associated with Manifest Lists.

        This call will not result in the units being deleted from Pulp itself, except for Tags since
        they are repository specific.

        :param repo:   metadata describing the repository
        :type  repo:   pulp.plugins.model.Repository
        :param units:  list of objects describing the units to import in
                       this call
        :type  units:  list of pulp.server.db.model.ContentUnit
        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        unit_removers = {
            models.Image: DockerImporter._remove_image,
            models.Manifest: DockerImporter._remove_manifest,
            models.ManifestList: DockerImporter._remove_manifest_list,
            models.Tag: DockerImporter._remove_tag
        }

        map((lambda u: type(u) in unit_removers and unit_removers[type(u)](
            repo.repo_obj, u)), units)

    @staticmethod
    def _remove_image(repo, image):
        """
        Purge tags associated with a given Image in the repository.

        :param repo:  The affected repository.
        :type  repo:  pulp.server.db.model.Repository
        :param image: The Image being removed
        :type  image: pulp_docker.plugins.models.Image
        """
        tags = repo.scratchpad.get(u'tags', [])
        for tag_dict in tags[:]:
            if tag_dict[constants.IMAGE_ID_KEY] == image.image_id:
                tags.remove(tag_dict)

        repo.scratchpad[u'tags'] = tags
        repo.save()

    @classmethod
    def _remove_manifest(cls, repo, manifest):
        """
        Purge Tags and Blobs associated with a given Manifest in the repository.

        :param repo:     The affected repository.
        :type  repo:     pulp.server.db.model.Repository
        :param manifest: The Manifest being removed
        :type  manifest: pulp_docker.plugins.models.Manifest
        """
        cls._purge_unlinked_tags(repo, manifest)
        cls._purge_unlinked_blobs(repo, manifest)

    @classmethod
    def _remove_manifest_list(cls, repo, manifest_list):
        """
        Purge Tags and image manifests associated with a given ManifestList in the repository.

        :param repo:     The affected repository.
        :type  repo:     pulp.server.db.model.Repository
        :param manifest_list: The ManifestList being removed
        :type  manifest_list: pulp_docker.plugins.models.ManifestList
        """
        cls._purge_unlinked_tags(repo, manifest_list)
        cls._purge_unlinked_manifests(repo, manifest_list)

    @classmethod
    def _remove_tag(cls, repo, tag):
        """
        Tags are repository-specific, so when they are removed, they should also be deleted.

        :param repo: unused
        :type  repo: pulp.server.db.model.Repository
        :param tag: Tag to be deleted
        :type  tag: pulp_docker.plugins.models.Tag
        """
        tag.delete()

    @staticmethod
    def _purge_unlinked_manifests(repo, manifest_list):

        # Find manifest digests referenced by removed manifest lists (orphaned)
        orphaned = set()
        for image_man in manifest_list.manifests:
            orphaned.add(image_man)
            if manifest_list.amd64_digest:
                orphaned.add(manifest_list.amd64_digest)
        if not orphaned:
            # nothing orphaned
            return

        # Find manifest digests still referenced by other manifest lists (adopted)
        adopted = set()
        criteria = UnitAssociationCriteria(type_ids=[constants.MANIFEST_LIST_TYPE_ID],
                                           unit_filters={'digest': {'$ne': manifest_list.digest}})
        for man_list in unit_association.RepoUnitAssociationManager._units_from_criteria(
                repo, criteria):
            for image_man in man_list.manifests:
                adopted.add(image_man)
            if man_list.amd64_digest:
                adopted.add(man_list.amd64_digest)

        # Remove unreferenced manifests
        orphaned = orphaned.difference(adopted)
        if not orphaned:
            # all adopted
            return

        # Check if those manifests have tags, tagged manifests cannot be removed
        criteria = UnitAssociationCriteria(
            type_ids=[constants.TAG_TYPE_ID],
            unit_filters={'manifest_digest': {'$in': list(orphaned)},
                          'manifest_type': constants.MANIFEST_IMAGE_TYPE})
        for tag in unit_association.RepoUnitAssociationManager._units_from_criteria(
                repo, criteria):
            orphaned.remove(tag.manifest_digest)

        unit_filter = {
            'digest': {
                '$in': sorted(orphaned)
            }
        }

        criteria = UnitAssociationCriteria(
            type_ids=[constants.MANIFEST_TYPE_ID],
            unit_filters=unit_filter)
        manager = manager_factory.repo_unit_association_manager()
        manager.unassociate_by_criteria(
            repo_id=repo.repo_id,
            criteria=criteria,
            notify_plugins=False)

        for manifest in models.Manifest.objects.filter(digest__in=sorted(orphaned)):
            DockerImporter._purge_unlinked_blobs(repo, manifest)

    @staticmethod
    def _purge_unlinked_tags(repo, manifest):
        """
        Purge Tags associated with the given Manifest (image or list) in the repository.
        We don't want to leave Tags that reference Manifests (image or lists) that no longer exist.

        :param repo:     The affected repository.
        :type  repo:     pulp.server.db.model.Repository
        :param manifest: The Manifest(image or list) that is being removed
        :type  manifest: pulp_docker.plugins.models.Manifest/ManifestList
        """
        # Find Tag objects that reference the removed Manifest. We can remove any such Tags from
        # the repository, and from Pulp as well (since Tag objects are repository specific).
        unit_filter = {'manifest_digest': manifest.digest}
        criteria = UnitAssociationCriteria(
            type_ids=[constants.TAG_TYPE_ID],
            unit_filters=unit_filter)
        manager = manager_factory.repo_unit_association_manager()
        manager.unassociate_by_criteria(
            repo_id=repo.repo_id,
            criteria=criteria,
            notify_plugins=False)
        # Finally, we can remove the Tag objects from Pulp entirely, since Tags are repository
        # specific.
        models.Tag.objects.filter(repo_id=repo.repo_id, manifest_digest=manifest.digest).delete()

    @staticmethod
    def _purge_unlinked_blobs(repo, manifest):
        """
        Purge blobs associated with the given Manifests when removing it would leave them no longer
        referenced by any remaining Manifests.

        :param repo:  The affected repository.
        :type  repo:  pulp.server.db.model.Repository
        :param units: List of removed units.
        :type  units: list of: pulp.plugins.model.AssociatedUnit
        """
        # Find blob digests referenced by removed manifests (orphaned)
        orphaned = set()
        map((lambda layer: orphaned.add(layer.blob_sum)), manifest.fs_layers)
        # in manifest schema version 2 there is an additional blob layer called config_layer
        if manifest.config_layer:
            orphaned.add(manifest.config_layer)
        if not orphaned:
            # nothing orphaned
            return

        # Find blob digests still referenced by other manifests (adopted)
        adopted = set()
        criteria = UnitAssociationCriteria(type_ids=[constants.MANIFEST_TYPE_ID],
                                           unit_filters={'digest': {'$ne': manifest.digest}})
        for manifest in unit_association.RepoUnitAssociationManager._units_from_criteria(
                repo, criteria):
            map((lambda layer: adopted.add(layer.blob_sum)), manifest.fs_layers)
            if manifest.config_layer:
                adopted.add(manifest.config_layer)

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
            type_ids=[constants.BLOB_TYPE_ID],
            unit_filters=unit_filter)
        manager = manager_factory.repo_unit_association_manager()
        manager.unassociate_by_criteria(
            repo_id=repo.repo_id,
            criteria=criteria,
            notify_plugins=False)
