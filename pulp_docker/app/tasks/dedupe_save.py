"""
Temporary module.

This module contains temporary replacements of several pulpcore stages that did not properly
duplicates within the stream. The entire module should be deleted after #4060 is finished.

https://pulp.plan.io/issues/4060

"""
from django.db import IntegrityError
from django.db.models import Q
from pulpcore.plugin.stages import Stage
from pulpcore.plugin.models import Artifact, ContentArtifact, RemoteArtifact

import logging
log = logging.getLogger(__name__)


class SerialArtifactSave(Stage):
    """
    Save Artifacts one at a time, combining duplicates.
    """

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
            out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` into.
        Returns:
            The coroutine for this stage.

        """
        while True:
            dc = await in_q.get()
            if dc is None:
                break
            self.save_and_dedupe_artifacts(dc)
            await out_q.put(dc)
        await out_q.put(None)

    def save_and_dedupe_artifacts(self, dc):
        """
        Save unique artifacts, combine duplicates.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
        """
        for da in dc.d_artifacts:
            artifact_q = Q()
            for digest_name in da.artifact.DIGEST_FIELDS:
                digest_value = getattr(da.artifact, digest_name)
                if digest_value:
                    key = {digest_name: digest_value}
                    artifact_q &= Q(**key)
            try:
                da.artifact.save()
            # ValueError raised by /home/vagrant/devel/pulp/pulpcore/pulpcore/app/models/fields.py",
            # line 32
            except (ValueError, IntegrityError):  # dupe
                existing_artifact = Artifact.objects.get(artifact_q)
                da.artifact = existing_artifact


class SerialContentSave(Stage):
    """
    Save Content one at a time, combining duplicates.
    """

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
            out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` into.
        Returns:
            The coroutine for this stage.

        """
        while True:
            dc = await in_q.get()
            # finished
            if dc is None:
                break

            # Do not save Content that contains Artifacts which have not been downloaded
            if not self.settled(dc):
                await out_q.put(dc)
            # already saved
            elif dc.content.pk is not None:
                await out_q.put(dc)
            else:
                self.save_and_dedupe_content(dc)
                await out_q.put(dc)
        await out_q.put(None)

    def save_and_dedupe_content(self, dc):
        """
        Combine duplicate Content, save unique Content.

        Args:
            dc (class:`~pulpcore.plugin.stages.DeclarativeContent`): Object containing Content to
                                                                     be saved.
        """
        model_type = type(dc.content)
        unit_key = dc.content.natural_key_dict()
        try:
            dc.content.save()
        except IntegrityError:
            existing_content = model_type.objects.get(**unit_key)
            dc.content = existing_content
            assert dc.content.pk is not None

        self.create_content_artifacts(dc)

    def create_content_artifacts(self, dc):
        """
        Create ContentArtifacts to associate saved Content to saved Artifacts.

        Args:
            dc (class:`~pulpcore.plugin.stages.DeclarativeContent`): Object containing Content and
                                                                     Artifacts to relate.
        """
        for da in dc.d_artifacts:
            content_artifact = ContentArtifact(
                content=dc.content,
                artifact=da.artifact,
                relative_path=da.relative_path
            )
            try:
                content_artifact.save()
            except IntegrityError:
                content_artifact = ContentArtifact.objects.get(
                    content=dc.content,
                    artifact=da.artifact,
                    relative_path=da.relative_path
                )

            remote_artifact_data = {
                'url': da.url,
                'size': da.artifact.size,
                'md5': da.artifact.md5,
                'sha1': da.artifact.sha1,
                'sha224': da.artifact.sha224,
                'sha256': da.artifact.sha256,
                'sha384': da.artifact.sha384,
                'sha512': da.artifact.sha512,
                'remote': da.remote,
            }
            new_remote_artifact = RemoteArtifact(
                content_artifact=content_artifact, **remote_artifact_data
            )
            try:
                new_remote_artifact.save()
            except IntegrityError:
                pass

    def settled(self, dc):
        """
        Indicates that all Artifacts in this dc are saved.

        Args:
            dc (class:`~pulpcore.plugin.stages.DeclarativeContent`): Object containing Artifacts
                                                                     that may be saved.

        Returns:
            bool: True when all Artifacts have been saved, False otherwise.

        """
        settled_dc = True
        for da in dc.d_artifacts:
            if da.artifact.pk is None:
                settled_dc = False
        return settled_dc
