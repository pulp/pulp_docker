from gettext import gettext as _
from urllib.parse import urljoin
import json
import logging

from django.db.models import Q

from pulpcore.plugin.models import Artifact, ProgressBar, Repository  # noqa
from pulpcore.plugin.stages import (
    DeclarativeArtifact,
    DeclarativeContent,
    DeclarativeVersion,
    Stage
)

# TODO(asmacdo) alphabetize
from pulp_docker.app.models import (ImageManifest, DockerRemote, MEDIA_TYPE, ManifestBlob,
                                    ManifestList, Tag)


# log = logging.getLogger(__name__)
tag_log = logging.getLogger("TAG")
list_log = logging.getLogger("****MANIFEST_LIST")
man_log = logging.getLogger("--------MANIFEST")
blob_log = logging.getLogger("++++++++++++++++BLOB")


V2_ACCEPT_HEADERS = {
    'accept': ','.join([MEDIA_TYPE.MANIFEST_V2, MEDIA_TYPE.MANIFEST_LIST])
}


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

    # TODO(asmacdo) self.remote is needed for Declarative artifacts, so needed by all plugins.
    # Add this to the base class?
    def __init__(self, remote):
        """
        The first stage of a pulp_docker sync pipeline.

        Args:
            remote (DockerRemote): The remote data to be used when syncing

        """
        self.remote = remote
        self.extra_request_data = {'headers': V2_ACCEPT_HEADERS}
        self._log_skipped_types = set()

    async def __call__(self, in_q, out_q):
        """
        Build and emit `DeclarativeContent` from the Manifest data.

        Args:
            in_q (asyncio.Queue): Unused because the first stage doesn't read from an input queue.
            out_q (asyncio.Queue): The out_q to send `DeclarativeContent` objects to

        """
        with ProgressBar(message="Downloading Tags List") as pb:
            tag_log.info("Fetching tags list for upstream repository: {repo}".format(
                repo=self.remote.upstream_name
            ))
            list_downloader = self.remote.get_downloader(self.tags_list_url)
            await list_downloader.run()

            with open(list_downloader.path) as tags_raw:
                tags_dict = json.loads(tags_raw.read())
                tag_list = tags_dict['tags']
            pb.increment()
        with ProgressBar(message="Downloading Tagged Manifests and Manifest Lists") as pb:
            for tag_name in tag_list:
                out_name = await self.download_and_process_tag(tag_name, out_q)
                tag_log.info("Done waiting on tag {name}".format(name=out_name))
                pb.increment()

        tag_log.warn("Skipped types: {ctypes}".format(ctypes=self._log_skipped_types))
        await out_q.put(None)

    async def download_and_process_tag(self, tag_name, out_q):
        # TODO(asmacdo) temporary, use all tags. need to add whitelist (sync.py#223)
        tag_url = self.get_tag_url(tag_name)
        # tag_log.info("Retriving tag from: {url}".format(url=tag_url))
        tag_downloader = self.remote.get_downloader(tag_url)
        # Accept headers indicate the highest version the client (us) can use.
        # The registry will return Manifests of this and lower type.
        # TODO(asmacdo) make this a constant?
        await tag_downloader.run(extra_data=self.extra_request_data)
        data_type = tag_downloader.response_headers['Content-Type']
        manifest_list = manifest = None
        if data_type == MEDIA_TYPE.MANIFEST_LIST:
            manifest_list = await self.process_manifest_list(tag_downloader, out_q)
        elif data_type == MEDIA_TYPE.MANIFEST_V2:
            # skipped_content_types.add(MEDIA_TYPE.MANIFEST_V2)
            manifest = await self.process_manifest(tag_downloader, out_q)
        else:
            self._log_skipped_types.add(data_type)
        tag = Tag(name=tag_name, manifest=manifest, manifest_list=manifest_list)
        tag_log.info("OUT: new tag")
        tag_dc = DeclarativeContent(content=tag)
        await out_q.put(tag_dc)
        return tag_name

    async def process_manifest_list(self, tag_downloader, out_q):
        with open(tag_downloader.path, 'rb') as manifest_file:
            raw = manifest_file.read()
        digests = {k: v for k, v in tag_downloader.artifact_attributes.items()
                   if k in Artifact.DIGEST_FIELDS}
        size = tag_downloader.artifact_attributes['size']
        manifest_list_data = json.loads(raw)
        manifest_list_artifact = Artifact(
            size=size,
            file=tag_downloader.path,
            **digests
        )
        da = DeclarativeArtifact(
            artifact=manifest_list_artifact,
            url=tag_downloader.url,
            relative_path=tag_downloader.path,
            remote=self.remote,
            extra_data=self.extra_request_data,
        )
        manifest_list = ManifestList(
            digest=digests['sha256'],
            schema_version=manifest_list_data['schemaVersion'],
            media_type=manifest_list_data['mediaType'],
            # artifacts=[manifest_list_artifact] TODO(asmacdo) does this get set?
        )
        try:
            manifest_list_artifact.save()
        except Exception as e:
            manifest_list_artifact = Artifact.objects.get(sha256=digests['sha256'])
        try:
            manifest_list.save()
        except Exception as e:
            list_log.info("Already created, using existing copy")
            manifest_list = ManifestList.objects.get(digest=manifest_list.digest)

        list_log.info("OUT: new list")
        list_dc = DeclarativeContent(content=manifest_list, d_artifacts=[da])
        await out_q.put(list_dc)
        # TODO(asmacdo)
        for manifest in manifest_list_data.get('manifests', []):
            downloaded = await self.download_manifest(manifest['digest'])
            await self.process_manifest(downloaded, out_q)

    async def download_manifest(self, reference):
        manifest_url = self.get_tag_url(reference)
        # man_log.info("Retriving manifest from: {url}".format(url=manifest_url))
        downloader = self.remote.get_downloader(manifest_url)
        # Accept headers indicate the highest version the client (us) can use.
        # The registry will return Manifests of this and lower type.
        # TODO(asmacdo) make this a constant?
        await downloader.run(extra_data=self.extra_request_data)
        return downloader

    async def process_manifest(self, downloader, out_q):
        with open(downloader.path, 'rb') as manifest_file:
            raw = manifest_file.read()
        digests = {k: v for k, v in downloader.artifact_attributes.items()
                   if k in Artifact.DIGEST_FIELDS}
        size = downloader.artifact_attributes['size']
        manifest_data = json.loads(raw)
        manifest_artifact = Artifact(
            size=size,
            file=downloader.path,
            **digests
        )
        da = DeclarativeArtifact(
            artifact=manifest_artifact,
            url=downloader.url,
            relative_path=downloader.path,
            remote=self.remote,
            extra_data=self.extra_request_data,
        )
        manifest = ImageManifest(
            digest=digests['sha256'],
            schema_version=manifest_data['schemaVersion'],
            media_type=manifest_data['mediaType'],
            # artifacts=[manifest_artifact] TODO(asmacdo) does this get set?
        )
        try:
            manifest_artifact.save()
        except Exception as e:
            manifest_artifact = Artifact.objects.get(sha256=digests['sha256'])
        try:
            manifest.save()
        except Exception as e:
            # man_log.info("using existing manifest")
            manifest = ImageManifest.objects.get(digest=manifest.digest)

        # man_log.info("Successful creation.")
        man_dc = DeclarativeContent(content=manifest, d_artifacts=[da])
        man_log.info("OUT new manifest list")
        await out_q.put(man_dc)
        # TODO(asmacdo) is [] default mutable?
        for layer in manifest_data.get('layers', []):
            await self.process_blob(layer, manifest, out_q)

    async def process_blob(self, layer, manifest, out_q):
        sha256 = layer['digest'][len('sha256:'):]
        blob_artifact = Artifact(
            size=layer['size'],
            sha256=sha256
            # Size not set, its not downloaded yet
        )
        blob = ManifestBlob(
            digest=sha256,
            media_type=layer['mediaType'],
            manifest=manifest
        )
        da = DeclarativeArtifact(
            artifact=blob_artifact,
            # Url should include 'sha256:'
            url=self.layer_url(layer['digest']),
            # TODO(asmacdo) is this what we want?
            relative_path=layer['digest'],
            remote=self.remote,
            # extra_data="TODO(asmacdo)"
        )
        dc = DeclarativeContent(content=blob, d_artifacts=[da])
        blob_log.info("OUTPUT new blob")
        await out_q.put(dc)

    def get_tag_url(self, tag):
        relative_url = '/v2/{name}/manifests/{tag}'.format(
            name=self.remote.namespaced_upstream_name,
            tag=tag
        )
        return urljoin(self.remote.url, relative_url)

    @property
    def tags_list_url(self):
        relative_url = '/v2/{name}/tags/list'.format(name=self.remote.namespaced_upstream_name)
        return urljoin(self.remote.url, relative_url)

    def layer_url(self, digest):
        relative_url = '/v2/{name}/blobs/{digest}'.format(
            name=self.remote.namespaced_upstream_name,
            digest=digest
        )
        return urljoin(self.remote.url, relative_url)


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
