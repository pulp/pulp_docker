from urllib.parse import urljoin
import json
import logging

from django.db import IntegrityError
from pulpcore.plugin.models import Artifact
from pulpcore.plugin.stages import DeclarativeArtifact, DeclarativeContent, Stage

from pulp_docker.app.models import (ImageManifest, MEDIA_TYPE, ManifestBlob, ManifestTag,
                                    ManifestList, ManifestListTag, BlobManifestBlob,
                                    ManifestListManifest)


log = logging.getLogger(__name__)


V2_ACCEPT_HEADERS = {
    'accept': ','.join([MEDIA_TYPE.MANIFEST_V2, MEDIA_TYPE.MANIFEST_LIST])
}


class TempTag:
    """
    This is a pseudo Tag that will either become a ManifestTag or a ManifestListTag.
    """

    def __init__(self, name):
        self.name = name


class TagListStage(Stage):
    """
    The first stage of a pulp_docker sync pipeline.
    """

    def __init__(self, remote):
        """Initialize the stage."""
        self.remote = remote

    async def __call__(self, in_q, out_q):
        """
        Build and emit `DeclarativeContent` for each Tag.

        Args:
            in_q (asyncio.Queue): Unused because the first stage doesn't read from an input queue.
            out_q (asyncio.Queue): Tag `DeclarativeContent` objects are sent here.

        """
        log.debug("Fetching tags list for upstream repository: {repo}".format(
            repo=self.remote.upstream_name
        ))
        relative_url = '/v2/{name}/tags/list'.format(name=self.remote.namespaced_upstream_name)
        tag_list_url = urljoin(self.remote.url, relative_url)
        list_downloader = self.remote.get_downloader(tag_list_url)
        await list_downloader.run()

        with open(list_downloader.path) as tags_raw:
            tags_dict = json.loads(tags_raw.read())
            tag_list = tags_dict['tags']

        for tag_name in tag_list:
            tag_dc = self.create_pending_tag(tag_name)
            await out_q.put(tag_dc)

        await out_q.put(None)

    def create_pending_tag(self, tag_name):
        """
        Create `DeclarativeContent` for each tag.

        Each dc contains enough information to be dowloaded by an ArtifactDownload Stage.

        Args:
            tag_name (str): Name of each tag

        Returns:
            pulpcore.plugin.stages.DeclarativeContent: A Tag DeclarativeContent object

        """
        relative_url = '/v2/{name}/manifests/{tag}'.format(
            name=self.remote.namespaced_upstream_name,
            tag=tag_name,
        )
        url = urljoin(self.remote.url, relative_url)
        tag = TempTag(name=tag_name)
        manifest_artifact = Artifact()
        da = DeclarativeArtifact(
            artifact=manifest_artifact,
            url=url,
            relative_path=tag_name,
            remote=self.remote,
            extra_data={'headers': V2_ACCEPT_HEADERS}
        )
        tag_dc = DeclarativeContent(content=tag, d_artifacts=[da])
        return tag_dc


class ProcessContentStage(Stage):
    """
    Process all Manifests, Manifest Lists, and Tags.

    For each processed type, create content from nested fields. This stage does not process
    ManifestBlobs, which do not contain nested content.
    """

    def __init__(self, remote):
        """
        Inform the stage about the remote to use.
        """
        self.remote = remote

    async def __call__(self, in_q, out_q):
        """
        Create new Content for all unsaved content units with downloaded artifacts.

        Args:
            in_q(asyncio.Queue): Queue of pulpcore.plugin.stages.DeclarativeContent objects to be
                                 processed.
            out_q(asyncio.Queue): Queue of pulpcore.plugin.stages.DeclarativeContent objects that
                                  have either been processed or were created in this stage.

        """
        while True:
            dc = await in_q.get()
            if dc is None:
                break
            elif dc.extra_data.get('processed'):
                await out_q.put(dc)
                continue
            elif type(dc.content) is ManifestBlob:
                await out_q.put(dc)
                continue

            # All docker content contains a single artifact.
            assert len(dc.d_artifacts) == 1
            with dc.d_artifacts[0].artifact.file.open() as content_file:
                raw = content_file.read()
            content_data = json.loads(raw)

            if type(dc.content) is TempTag:
                if content_data.get('mediaType') == MEDIA_TYPE.MANIFEST_LIST:
                    await self.create_and_process_tagged_manifest_list(dc, content_data, out_q)
                    await out_q.put(dc)
                elif content_data.get('mediaType') == MEDIA_TYPE.MANIFEST_V2:
                    await self.create_and_process_tagged_manifest(dc, content_data, out_q)
                    await out_q.put(dc)
                else:
                    assert content_data.get('schemaVersion') == 1
            elif type(dc.content) is ImageManifest:
                for layer in content_data.get("layers"):
                    blob_dc = await self.create_pending_blob(dc, layer, out_q)
                    blob_dc.extra_data['relation'] = dc
                    await out_q.put(blob_dc)

                config_layer = content_data.get('config')
                if config_layer:
                    config_blob_dc = await self.create_pending_blob(dc, config_layer, out_q)
                    config_blob_dc.extra_data['config_relation'] = dc
                    await out_q.put(config_blob_dc)
                dc.extra_data['processed'] = True
                await out_q.put(dc)
            else:
                msg = "Unexpected type cannot be processed{tp}".format(tp=type(dc.content))
                raise Exception(msg)

        await out_q.put(None)

    async def create_and_process_tagged_manifest_list(self, tag_dc, manifest_list_data, out_q):
        """
        Create a ManifestList and nested ImageManifests from the Tag artifact.

        Args:
            tag_dc (pulpcore.plugin.stages.DeclarativeContent): dc for a Tag
            manifest_list_data (dict): Data about a ManifestList
            out_q (asyncio.Queue): Queue to put created ManifestList and ImageManifest dcs.
        """
        tag_dc.content = ManifestListTag(name=tag_dc.content.name)
        digest = "sha256:{digest}".format(digest=tag_dc.d_artifacts[0].artifact.sha256)
        relative_url = '/v2/{name}/manifests/{digest}'.format(
            name=self.remote.namespaced_upstream_name,
            digest=digest,
        )
        url = urljoin(self.remote.url, relative_url)
        manifest_list = ManifestList(
            digest=digest,
            schema_version=manifest_list_data['schemaVersion'],
            media_type=manifest_list_data['mediaType'],
        )
        da = DeclarativeArtifact(
            artifact=tag_dc.d_artifacts[0].artifact,
            url=url,
            relative_path=digest,
            remote=self.remote,
            extra_data={'headers': V2_ACCEPT_HEADERS}
        )
        list_dc = DeclarativeContent(content=manifest_list, d_artifacts=[da])
        for manifest in manifest_list_data.get('manifests'):
            await self.create_pending_manifest(list_dc, manifest, out_q)
        list_dc.extra_data['relation'] = tag_dc
        list_dc.extra_data['processed'] = True
        tag_dc.extra_data['processed'] = True
        await out_q.put(list_dc)

    async def create_and_process_tagged_manifest(self, tag_dc, manifest_data, out_q):
        """
        Create a Manifest and nested ManifestBlobs from the Tag artifact.

        Args:
            tag_dc (pulpcore.plugin.stages.DeclarativeContent): dc for a Tag
            manifest_data (dict): Data about a single new ImageManifest.
            out_q (asyncio.Queue): Queue to put created ImageManifest dcs and Blob dcs.
        """
        tag_dc.content = ManifestTag(name=tag_dc.content.name)
        manifest = ImageManifest(
            digest=tag_dc.d_artifacts[0].artifact.sha256,
            schema_version=manifest_data['schemaVersion'],
            media_type=manifest_data['mediaType'],
        )
        man_dc = DeclarativeContent(content=manifest, d_artifacts=[tag_dc.d_artifacts[0]])
        for layer in manifest_data.get('layers'):
            blob_dc = await self.create_pending_blob(man_dc, layer, out_q)
            blob_dc.extra_data['relation'] = man_dc
            await out_q.put(blob_dc)
        config_layer = manifest_data.get('config')
        if config_layer:
            config_blob_dc = await self.create_pending_blob(man_dc, config_layer, out_q)
            config_blob_dc.extra_data['config_relation'] = man_dc
            await out_q.put(config_blob_dc)

        man_dc.extra_data['relation'] = tag_dc
        tag_dc.extra_data['processed'] = True
        man_dc.extra_data['processed'] = True
        await out_q.put(man_dc)

    async def create_pending_manifest(self, list_dc, manifest_data, out_q):
        """
        Create a pending manifest from manifest data in a ManifestList.

        Args:
            list_dc (pulpcore.plugin.stages.DeclarativeContent): dc for a ManifestList
            manifest_data (dict): Data about a single new ImageManifest.
            out_q (asyncio.Queue): Queue to put created ImageManifest dcs.
        """
        digest = manifest_data['digest']
        relative_url = '/v2/{name}/manifests/{digest}'.format(
            name=self.remote.namespaced_upstream_name,
            digest=digest
        )
        manifest_url = urljoin(self.remote.url, relative_url)
        manifest_artifact = Artifact(sha256=digest[len("sha256:"):])
        da = DeclarativeArtifact(
            artifact=manifest_artifact,
            url=manifest_url,
            relative_path=digest,
            remote=self.remote,
            extra_data={'headers': V2_ACCEPT_HEADERS}
        )
        manifest = ImageManifest(
            digest=manifest_data['digest'],
            schema_version=2,
            media_type=manifest_data['mediaType'],
        )
        man_dc = DeclarativeContent(
            content=manifest,
            d_artifacts=[da],
            extra_data={'relation': list_dc}
        )
        await out_q.put(man_dc)

    async def create_pending_blob(self, man_dc, blob_data, out_q):
        """
        Create a pending blob from a layer in the ImageManifest.

        Args:
            man_dc (pulpcore.plugin.stages.DeclarativeContent): dc for an ImageManifest
            blob_data (dict): Data about a single new blob.
            out_q (asyncio.Queue): Queue to put created blob dcs.

        """
        digest = blob_data['digest']
        blob_artifact = Artifact(sha256=digest[len("sha256:"):])
        blob = ManifestBlob(
            digest=digest,
            media_type=blob_data['mediaType'],
        )
        relative_url = '/v2/{name}/blobs/{digest}'.format(
            name=self.remote.namespaced_upstream_name,
            digest=blob_data['digest'],
        )
        blob_url = urljoin(self.remote.url, relative_url)
        da = DeclarativeArtifact(
            artifact=blob_artifact,
            url=blob_url,
            relative_path=blob_data['digest'],
            remote=self.remote,
            extra_data={'headers': V2_ACCEPT_HEADERS}
        )
        blob_dc = DeclarativeContent(
            content=blob,
            d_artifacts=[da],
        )
        return blob_dc


class InterrelateContent(Stage):
    """
    Stage for relating Content to other Content.
    """

    async def __call__(self, in_q, out_q):
        """
        Relate each item in the in_q to objects specified on the DeclarativeContent.

        Args:
            in_q (asyncio.Queue): A queue of unrelated pulpcore.plugin.DeclarativeContent objects
            out_q (asyncio.Queue): A queue of unrelated pulpcore.plugin.DeclarativeContent objects
        """
        while True:
            dc = await in_q.get()
            if dc is None:
                break
            if dc.extra_data.get('relation'):
                if type(dc.content) is ManifestList:
                    self.relate_manifest_list(dc)
                elif type(dc.content) is ManifestBlob:
                    self.relate_blob(dc)
                elif type(dc.content) is ImageManifest:
                    self.relate_manifest(dc)

            configured_dc = dc.extra_data.get('config_relation')
            if configured_dc:
                configured_dc.content.config_blob = dc.content
                configured_dc.content.save()

            await out_q.put(dc)
        await out_q.put(None)

    def relate_blob(self, dc):
        """
        Relate a ManifestBlob to a Manifest.

        Args:
            dc (pulpcore.plugin.stages.DeclarativeContent): dc for a ManifestList
        """
        related_dc = dc.extra_data.get('relation')
        assert related_dc is not None
        thru = BlobManifestBlob(manifest=related_dc.content, manifest_blob=dc.content)
        try:
            thru.save()
        except IntegrityError:
            pass

    def relate_manifest(self, dc):
        """
        Relate an ImageManifest to a Tag or ManifestList.

        Args:
            dc (pulpcore.plugin.stages.DeclarativeContent): dc for a ManifestList
        """
        related_dc = dc.extra_data.get('relation')
        assert related_dc is not None
        if type(related_dc.content) is ManifestTag:
            assert related_dc.content.manifest is None
            related_dc.content.manifest = dc.content
            try:
                related_dc.content.save()
            except IntegrityError:
                existing_tag = ManifestTag.objects.get(name=related_dc.content.name,
                                                       manifest=dc.content)
                related_dc.content = existing_tag
        elif type(related_dc.content) is ManifestList:
            thru = ManifestListManifest(manifest_list=related_dc.content, manifest=dc.content)
            try:
                thru.save()
            except IntegrityError:
                pass

    def relate_manifest_list(self, dc):
        """
        Relate a ManifestList to a Tag.

        Args:
            dc (pulpcore.plugin.stages.DeclarativeContent): dc for a ManifestList
        """
        related_dc = dc.extra_data.get('relation')
        assert type(related_dc.content) is ManifestListTag
        assert related_dc.content.manifest_list is None
        related_dc.content.manifest_list = dc.content
        try:
            related_dc.content.save()
        except IntegrityError:
            existing_tag = ManifestListTag.objects.get(name=related_dc.content.name,
                                                       manifest_list=dc.content)
            related_dc.content = existing_tag
