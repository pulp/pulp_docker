import asyncio
import json
import logging

from gettext import gettext as _
from urllib.parse import urljoin

from django.db import IntegrityError
from pulpcore.plugin.models import Artifact, ProgressBar
from pulpcore.plugin.stages import DeclarativeArtifact, DeclarativeContent, Stage

from pulp_docker.app.models import (ImageManifest, MEDIA_TYPE, ManifestBlob, ManifestTag,
                                    ManifestList, ManifestListTag, BlobManifestBlob,
                                    ManifestListManifest)


log = logging.getLogger(__name__)


V2_ACCEPT_HEADERS = {
    'accept': ','.join([MEDIA_TYPE.MANIFEST_V2, MEDIA_TYPE.MANIFEST_LIST])
}


class DockerFirstStage(Stage):
    """
    The first stage of a pulp_docker sync pipeline.

    In this stage all the content is discovered, including the nested one.

    """

    def __init__(self, remote):
        """Initialize the stage."""
        super().__init__()
        self.remote = remote

    async def run(self):
        """
        DockerFirstStage.
        """
        future_manifests = []
        tag_list = []
        to_download = []
        man_dcs = {}
        total_blobs = []

        with ProgressBar(message='Downloading tag list', total=1) as pb:
            relative_url = '/v2/{name}/tags/list'.format(name=self.remote.namespaced_upstream_name)
            tag_list_url = urljoin(self.remote.url, relative_url)
            list_downloader = self.remote.get_downloader(tag_list_url)
            await list_downloader.run()

            with open(list_downloader.path) as tags_raw:
                tags_dict = json.loads(tags_raw.read())
                tag_list = tags_dict['tags']

            pb.increment()

        with ProgressBar(message='Creating Download requests for Tags', total=len(tag_list)) as pb:
            for tag_name in tag_list:
                relative_url = '/v2/{name}/manifests/{tag}'.format(
                    name=self.remote.namespaced_upstream_name,
                    tag=tag_name,
                )
                url = urljoin(self.remote.url, relative_url)
                downloader = self.remote.get_downloader(url=url)
                to_download.append(downloader.run(extra_data={'headers': V2_ACCEPT_HEADERS}))
                pb.increment()

        pb_parsed_tags = ProgressBar(message='Parsing SchemaV2 Tags', state='running')
        pb_parsed_ml_tags = ProgressBar(message='Parsing Manifest List Tags', state='running')
        pb_parsed_m_tags = ProgressBar(message='Parsing Manifests Tags', state='running')
        global pb_parsed_blobs
        pb_parsed_blobs = ProgressBar(message='Parsing Blobs', state='running')
        pb_parsed_man = ProgressBar(message='Parsing Manifests', state='running')

        for download_tag in asyncio.as_completed(to_download):
            tag = await download_tag
            with open(tag.path) as content_file:
                raw = content_file.read()
            content_data = json.loads(raw)
            mediatype = content_data.get('mediaType')
            if mediatype:
                tag.artifact_attributes['file'] = tag.path
                saved_artifact = Artifact(**tag.artifact_attributes)
                try:
                    saved_artifact.save()
                except IntegrityError:
                    del tag.artifact_attributes['file']
                    saved_artifact = Artifact.objects.get(**tag.artifact_attributes)
                tag_dc = self.create_tag(mediatype, saved_artifact, tag.url)
                if type(tag_dc.content) is ManifestListTag:
                    list_dc = self.create_tagged_manifest_list(
                        tag_dc, content_data)
                    await self.put(list_dc)
                    pb_parsed_ml_tags.increment()
                    tag_dc.extra_data['list_relation'] = list_dc
                    for manifest_data in content_data.get('manifests'):
                        man_dc = self.create_manifest(list_dc, manifest_data)
                        future_manifests.append(man_dc.get_or_create_future())
                        man_dcs[man_dc.content.digest] = man_dc
                        await self.put(man_dc)
                        pb_parsed_man.increment()
                elif type(tag_dc.content) is ManifestTag:
                    man_dc = self.create_tagged_manifest(tag_dc, content_data)
                    await self.put(man_dc)
                    pb_parsed_m_tags.increment()
                    tag_dc.extra_data['man_relation'] = man_dc
                    self.handle_blobs(man_dc, content_data, total_blobs)
                await self.put(tag_dc)
                pb_parsed_tags.increment()
            else:
                # in case it is a schema1 continue to the next tag
                continue

        pb_parsed_tags.state = 'completed'
        pb_parsed_tags.total = pb_parsed_tags.done
        pb_parsed_tags.save()
        pb_parsed_ml_tags.state = 'completed'
        pb_parsed_ml_tags.total = pb_parsed_ml_tags.done
        pb_parsed_ml_tags.save()
        pb_parsed_m_tags.state = 'completed'
        pb_parsed_m_tags.total = pb_parsed_m_tags.done
        pb_parsed_m_tags.save()
        pb_parsed_man.state = 'completed'
        pb_parsed_man.total = pb_parsed_man.done
        pb_parsed_man.save()

        for manifest_future in asyncio.as_completed(future_manifests):
            man = await manifest_future
            with man._artifacts.get().file.open() as content_file:
                raw = content_file.read()
            content_data = json.loads(raw)
            man_dc = man_dcs[man.digest]
            self.handle_blobs(man_dc, content_data, total_blobs)
        for blob in total_blobs:
            await self.put(blob)

        pb_parsed_blobs.state = 'completed'
        pb_parsed_blobs.total = pb_parsed_blobs.done
        pb_parsed_blobs.save()

    def handle_blobs(self, man, content_data, total_blobs):
        """
        Handle blobs.
        """
        for layer in content_data.get("layers"):
            if not self._include_layer(layer):
                continue
            blob_dc = self.create_blob(man, layer)
            blob_dc.extra_data['blob_relation'] = man
            total_blobs.append(blob_dc)
            pb_parsed_blobs.increment()
        layer = content_data.get('config')
        blob_dc = self.create_blob(man, layer)
        blob_dc.extra_data['config_relation'] = man
        pb_parsed_blobs.increment()
        total_blobs.append(blob_dc)

    def create_tag(self, mediatype, saved_artifact, url):
        """
        Create `DeclarativeContent` for each tag.

        Each dc contains enough information to be dowloaded by an ArtifactDownload Stage.

        Args:
            tag_name (str): Name of each tag

        Returns:
            pulpcore.plugin.stages.DeclarativeContent: A Tag DeclarativeContent object

        """
        tag_name = url.split('/')[-1]
        relative_url = '/v2/{name}/manifests/{tag}'.format(
            name=self.remote.namespaced_upstream_name,
            tag=tag_name,
        )
        url = urljoin(self.remote.url, relative_url)
        if mediatype == MEDIA_TYPE.MANIFEST_LIST:
            tag = ManifestListTag(name=tag_name)
        elif mediatype == MEDIA_TYPE.MANIFEST_V2:
            tag = ManifestTag(name=tag_name)
        da = DeclarativeArtifact(
            artifact=saved_artifact,
            url=url,
            relative_path=tag_name,
            remote=self.remote,
            extra_data={'headers': V2_ACCEPT_HEADERS}
        )
        tag_dc = DeclarativeContent(content=tag, d_artifacts=[da])
        return tag_dc

    def create_tagged_manifest_list(self, tag_dc, manifest_list_data):
        """
        Create a ManifestList.

        Args:
            tag_dc (pulpcore.plugin.stages.DeclarativeContent): dc for a Tag
            manifest_list_data (dict): Data about a ManifestList
        """
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

        return list_dc

    def create_tagged_manifest(self, tag_dc, manifest_data):
        """
        Create an Image Manifest.

        Args:
            tag_dc (pulpcore.plugin.stages.DeclarativeContent): dc for a Tag
            manifest_data (dict): Data about a single new ImageManifest.
        """
        digest = "sha256:{digest}".format(digest=tag_dc.d_artifacts[0].artifact.sha256)
        manifest = ImageManifest(
            digest=digest,
            schema_version=manifest_data['schemaVersion'],
            media_type=manifest_data['mediaType'],
        )
        relative_url = '/v2/{name}/manifests/{digest}'.format(
            name=self.remote.namespaced_upstream_name,
            digest=digest,
        )
        url = urljoin(self.remote.url, relative_url)
        da = DeclarativeArtifact(
            artifact=tag_dc.d_artifacts[0].artifact,
            url=url,
            relative_path=digest,
            remote=self.remote,
            extra_data={'headers': V2_ACCEPT_HEADERS}
        )
        man_dc = DeclarativeContent(content=manifest, d_artifacts=[da])
        return man_dc

    def create_manifest(self, list_dc, manifest_data):
        """
        Create an Image Manifest from manifest data in a ManifestList.

        Args:
            list_dc (pulpcore.plugin.stages.DeclarativeContent): dc for a ManifestList
            manifest_data (dict): Data about a single new ImageManifest.
        """
        digest = manifest_data['digest']
        relative_url = '/v2/{name}/manifests/{digest}'.format(
            name=self.remote.namespaced_upstream_name,
            digest=digest
        )
        manifest_url = urljoin(self.remote.url, relative_url)
        da = DeclarativeArtifact(
            artifact=Artifact(),
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
            extra_data={'relation': list_dc},
            does_batch=False,
        )
        return man_dc

    def create_blob(self, man_dc, blob_data):
        """
        Create blob.

        Args:
            man_dc (pulpcore.plugin.stages.DeclarativeContent): dc for a ImageManifest
            blob_data (dict): Data about a blob

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

    def _include_layer(self, layer):
        """
        Decide whether to include a layer.

        Args:
            layer (dict): Layer reference.

        Returns:
            bool: True when the layer should be included.

        """
        foreign_excluded = (not self.remote.include_foreign_layers)
        is_foreign = (layer.get('mediaType') == MEDIA_TYPE.FOREIGN_BLOB)
        if is_foreign and foreign_excluded:
            log.debug(_('Foreign Layer: %(d)s EXCLUDED'), dict(d=layer))
            return False
        return True


class InterrelateContent(Stage):
    """
    Stage for relating Content to other Content.
    """

    async def run(self):
        """
        Relate each item in the input queue to objects specified on the DeclarativeContent.
        """
        async for dc in self.items():

            if dc.extra_data.get('relation'):
                self.relate_manifest_to_list(dc)
            elif dc.extra_data.get('blob_relation'):
                self.relate_blob(dc)
            elif dc.extra_data.get('config_relation'):
                self.relate_config_blob(dc)
            elif dc.extra_data.get('list_relation'):
                self.relate_manifest_list(dc)
            elif dc.extra_data.get('man_relation'):
                self.relate_manifest(dc)

            await self.put(dc)

    def relate_config_blob(self, dc):
        """
        Relate a ManifestBlob to a Manifest as a config layer.

        Args:
            dc (pulpcore.plugin.stages.DeclarativeContent): dc for a Blob
        """
        configured_dc = dc.extra_data.get('config_relation')
        configured_dc.content.config_blob = dc.content
        configured_dc.content.save()

    def relate_blob(self, dc):
        """
        Relate a ManifestBlob to a Manifest.

        Args:
            dc (pulpcore.plugin.stages.DeclarativeContent): dc for a Blob
        """
        related_dc = dc.extra_data.get('blob_relation')
        thru = BlobManifestBlob(manifest=related_dc.content, manifest_blob=dc.content)
        try:
            thru.save()
        except IntegrityError:
            pass

    def relate_manifest(self, dc):
        """
        Relate an ImageManifest to a Tag.

        Args:
            dc (pulpcore.plugin.stages.DeclarativeContent): dc for a ManifestTag
        """
        related_dc = dc.extra_data.get('man_relation')
        assert dc.content.manifest is None
        dc.content.manifest = related_dc.content
        try:
            dc.content.save()
        except IntegrityError:
            existing_tag = ManifestTag.objects.get(name=dc.content.name,
                                                   manifest=related_dc.content)
            dc.content = existing_tag

    def relate_manifest_to_list(self, dc):
        """
        Relate an ImageManifest to a ManifestList.

        Args:
            dc (pulpcore.plugin.stages.DeclarativeContent): dc for a ImageManifest
        """
        related_dc = dc.extra_data.get('relation')
        thru = ManifestListManifest(manifest_list=related_dc.content, manifest=dc.content)
        try:
            thru.save()
        except IntegrityError:
            pass

    def relate_manifest_list(self, dc):
        """
        Relate a ManifestList to a Tag.

        Args:
            dc (pulpcore.plugin.stages.DeclarativeContent): dc for a ManifestListTag
        """
        related_dc = dc.extra_data.get('list_relation')
        assert dc.content.manifest_list is None
        dc.content.manifest_list = related_dc.content
        try:
            dc.content.save()
        except IntegrityError:

            existing_tag = ManifestListTag.objects.get(name=dc.content.name,
                                                       manifest_list=related_dc.content)
            dc.content = existing_tag
            pass
