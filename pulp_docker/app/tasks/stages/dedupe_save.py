from django.db.models import Q
from pulpcore.plugin.stages import Stage
from pulpcore.plugin.models import Artifact, ContentArtifact, ProgressBar, RemoteArtifact

# from pulp_docker.app.models import ManifestList, ImageManifest, ManifestBlob

import logging
log = logging.getLogger("STUPIDSAVE")


class SerialArtifactSave(Stage):
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
            self.query_and_save_artifacts(dc)
            await out_q.put(dc)
        await out_q.put(None)

    def query_and_save_artifacts(self, dc):
        for da in dc.d_artifacts:
            artifact_q = Q()
            for digest_name in da.artifact.DIGEST_FIELDS:
                digest_value = getattr(da.artifact, digest_name)
                if digest_value:
                    key = {digest_name: digest_value}
                    artifact_q &= Q(**key)
            try:
                existing_artifact = Artifact.objects.get(artifact_q)
                # TODO count deduped artifacts
            except Artifact.DoesNotExist as e:
                da.artifact.save()
            else:
                da.artifact = existing_artifact


class SerialContentSave(Stage):
    async def __call__(self, in_q, out_q):
        while True:
            dc = await in_q.get()
            # finished
            if dc is None:
                break
            # Artifacts have not been downloaded
            elif not self.settled(dc):
                await out_q.put(dc)
            # already saved
            elif dc.content.pk is not None:
                await out_q.put(dc)
            # needs to be saved
            else:
                self.query_and_save_content(dc)
                await out_q.put(dc)
        await out_q.put(None)

    def query_and_save_content(self, dc):
        model_type = type(dc.content)
        unit_key = dc.content.natural_key_dict()
        try:
            existing_content = model_type.objects.get(**unit_key)
            # TODO count deduped artifacts
        except model_type.DoesNotExist as e:
            dc.content.save()
            self.create_content_artifacts(dc)
        else:
            dc.content = existing_content

    def create_content_artifacts(self, dc):
        for da in dc.d_artifacts:
            content_artifact = ContentArtifact(
                content=dc.content,
                artifact=da.artifact,
                relative_path=da.relative_path
            )
            # should always work, content is new
            content_artifact.save()
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
            new_remote_artifact.save()

    def settled(self, dc):
        settled_dc = True
        for da in dc.d_artifacts:
            if da.artifact.pk is None:
                settled_dc = False
        return settled_dc
