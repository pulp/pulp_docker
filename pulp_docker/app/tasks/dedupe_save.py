"""
Temporary module.

This module contains temporary replacements of several pulpcore stages that did not properly
duplicates within the stream. The entire module should be deleted after #4060 is finished.

https://pulp.plan.io/issues/4060

"""
from django.db import IntegrityError
from pulpcore.plugin.stages import Stage
from pulpcore.plugin.models import ContentArtifact, RemoteArtifact

import logging
log = logging.getLogger(__name__)


class SerialContentSave(Stage):
    """
    Save Content one at a time, combining duplicates.
    """

    async def run(self):
        """
        The coroutine for this stage.

        Returns:
            The coroutine for this stage.

        """
        async for dc in self.items():
            # Do not save Content that contains Artifacts which have not been downloaded
            if not self.settled(dc):
                await self.put(dc)
            # already saved
            elif dc.content.pk is not None:
                await self.put(dc)
            else:
                self.save_and_dedupe_content(dc)
                await self.put(dc)

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
