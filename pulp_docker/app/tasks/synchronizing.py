from gettext import gettext as _
import logging

from django.db.models import Q

from pulpcore.plugin.models import Artifact, ProgressBar, Repository  # noqa
from pulpcore.plugin.stages import (
    DeclarativeArtifact,
    DeclarativeContent,
    DeclarativeVersion,
    Stage
)

from pulp_docker.app.models import ImageManifest, DockerRemote


log = logging.getLogger(__name__)


def synchronize(remote_pk, repository_pk):
    """
    Sync content from the remote repository.

    Create a new version of the repository that is synchronized with the remote.

    Args:
        remote_pk (str): The remote PK.
        repository_pk (str): The repository PK.

    Raises:
        ValueError: If the remote does not specify a URL to sync

    """
    remote = DockerRemote.objects.get(pk=remote_pk)
    repository = Repository.objects.get(pk=repository_pk)

    if not remote.url:
        raise ValueError(_('A remote must have a url specified to synchronize.'))

    first_stage = DockerFirstStage(remote)
    DeclarativeVersion(first_stage, repository).create()


class DockerFirstStage(Stage):
    """
    The first stage of a pulp_docker sync pipeline.
    """

    def __init__(self, remote):
        """
        The first stage of a pulp_docker sync pipeline.

        Args:
            remote (FileRemote): The remote data to be used when syncing

        """
        self.remote = remote

    async def __call__(self, in_q, out_q):
        """
        Build and emit `DeclarativeContent` from the Manifest data.

        Args:
            in_q (asyncio.Queue): Unused because the first stage doesn't read from an input queue.
            out_q (asyncio.Queue): The out_q to send `DeclarativeContent` objects to

        """
        downloader = self.remote.get_downloader(self.remote.url)
        result = await downloader.run()
        # Use ProgressBar to report progress
        for entry in self.read_my_metadata_file_somehow(result.path):
            unit = ImageManifest(entry)  # make the content unit in memory-only
            artifact = Artifact(entry)  # make Artifact in memory-only
            da = DeclarativeArtifact(artifact, entry.url, entry.relative_path, self.remote)
            dc = DeclarativeContent(content=unit, d_artifacts=[da])
            await out_q.put(dc)
        await out_q.put(None)

    def read_my_metadata_file_somehow(self, path):
        """
        Parse the metadata for docker Content type.

        Args:
            path: Path to the metadata file
        """
        pass


class QueryAndSaveArtifacts(Stage):
    """
    The stage that bulk saves only the artifacts that have not been saved before.

    A stage that replaces :attr:`DeclarativeContent.d_artifacts` objects with
    already-saved :class:`~pulpcore.plugin.models.Artifact` objects.

    This stage expects :class:`~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and
    inspects their associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object stores one
    :class:`~pulpcore.plugin.models.Artifact`.

    This stage inspects any unsaved :class:`~pulpcore.plugin.models.Artifact` objects and searches
    using their metadata for existing saved :class:`~pulpcore.plugin.models.Artifact` objects inside
    Pulp with the same digest value(s). Any existing :class:`~pulpcore.plugin.models.Artifact`
    objects found will replace their unsaved counterpart in the
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object. Each remaining unsaved
    :class:`~pulpcore.plugin.models.Artifact` is saved.

    Each :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to `out_q` after all of its
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage drains all available items from `in_q` and batches everything into one large call to
    the db for efficiency.

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
        async for batch in self.batches(in_q):
            all_artifacts_q = Q(pk=None)
            for content in batch:
                for declarative_artifact in content.d_artifacts:
                    one_artifact_q = Q()
                    for digest_name in declarative_artifact.artifact.DIGEST_FIELDS:
                        digest_value = getattr(declarative_artifact.artifact, digest_name)
                        if digest_value:
                            key = {digest_name: digest_value}
                            one_artifact_q &= Q(**key)
                    if one_artifact_q:
                        all_artifacts_q |= one_artifact_q

            for artifact in Artifact.objects.filter(all_artifacts_q):
                for content in batch:
                    for declarative_artifact in content.d_artifacts:
                        for digest_name in artifact.DIGEST_FIELDS:
                            digest_value = getattr(declarative_artifact.artifact, digest_name)
                            if digest_value and digest_value == getattr(artifact, digest_name):
                                declarative_artifact.artifact = artifact
                                break

            artifacts_to_save = []

            for declarative_content in batch:
                for declarative_artifact in declarative_content.d_artifacts:
                    if declarative_artifact.artifact.pk is None:
                        declarative_artifact.artifact.file = str(
                            declarative_artifact.artifact.file)
                        artifacts_to_save.append(declarative_artifact.artifact)

            if artifacts_to_save:
                Artifact.objects.bulk_create(artifacts_to_save)

            for declarative_content in batch:
                await out_q.put(declarative_content)
        await out_q.put(None)
