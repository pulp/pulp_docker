from logging import getLogger
from types import SimpleNamespace

from django.db import models

from pulpcore.plugin.models import Content, Remote, Publisher


logger = getLogger(__name__)


MEDIA_TYPE = SimpleNamespace(
    MANIFEST_V1='application/vnd.docker.distribution.manifest.v1+json',
    MANIFEST_V2='application/vnd.docker.distribution.manifest.v2+json',
    MANIFEST_LIST='application/vnd.docker.distribution.manifest.list.v2+json',
    CONFIG_BLOB='application/vnd.docker.container.image.v1+json',
    REGULAR_BLOB='application/vnd.docker.image.rootfs.diff.tar.gzip',
    FOREIGN_BLOB='application/vnd.docker.image.rootfs.foreign.diff.tar.gzip',
)


class ImageManifest(Content):
    """
    A docker manifest.

    This content has one artifact.

    Fields:
        digest (models.CharField): The manifest digest.
        schema_version (models.IntegerField): The docker schema version.
        media_type (models.CharField): The manifest media type.
    """

    TYPE = 'manifest'

    digest = models.CharField(max_length=255)
    schema_version = models.IntegerField()
    media_type = models.CharField(
        max_length=60,
        choices=(
            (MEDIA_TYPE.MANIFEST_V1, MEDIA_TYPE.MANIFEST_V1),
            (MEDIA_TYPE.MANIFEST_V2, MEDIA_TYPE.MANIFEST_V2),
        ))

    class Meta:
        unique_together = ('digest',)


class ManifestBlob(Content):
    """
    A blob defined within a manifest.

    The actual blob file is stored as an artifact.

    Fields:
        digest (models.CharField): The blob digest.
        media_type (models.CharField): The blob media type.

    Relations:
        manifest (models.ForeignKey): Many-to-one relationship with Manifest.
    """

    TYPE = 'manifest-blob'

    digest = models.CharField(max_length=255)
    media_type = models.CharField(
        max_length=80,
        choices=(
            (MEDIA_TYPE.CONFIG_BLOB, MEDIA_TYPE.CONFIG_BLOB),
            (MEDIA_TYPE.REGULAR_BLOB, MEDIA_TYPE.REGULAR_BLOB),
            (MEDIA_TYPE.FOREIGN_BLOB, MEDIA_TYPE.FOREIGN_BLOB),
        ))

    manifest = models.ForeignKey(ImageManifest, related_name='blobs', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('digest',)


class ManifestList(Content):
    """
    A manifest list.

    This content has one artifact.

    Fields:
        digest (models.CharField): The manifest digest.
        schema_version (models.IntegerField): The docker schema version.
        media_type (models.CharField): The manifest media type.

    Relations:
        manifests (models.ManyToManyField): Many-to-many relationship with Manifest.
    """

    TYPE = 'manifest-list'

    digest = models.CharField(max_length=255)
    schema_version = models.IntegerField()
    media_type = models.CharField(
        max_length=60,
        choices=(
            (MEDIA_TYPE.MANIFEST_LIST, MEDIA_TYPE.MANIFEST_LIST),
        ))

    manifests = models.ManyToManyField(ImageManifest, through='ManifestListManifest')

    class Meta:
        unique_together = ('digest',)


class ManifestListManifest(models.Model):
    """
    The manifest referenced by a manifest list.

    Fields:
        architecture (models.CharField): The platform architecture.
        variant (models.CharField): The platform variant.
        features (models.TextField): The platform features.
        os (models.CharField): The platform OS name.
        os_version (models.CharField): The platform OS version.
        os_features (models.TextField): The platform OS features.

    Relations:
        manifest (models.ForeignKey): Many-to-one relationship with Manifest.
        manifest_list (models.ForeignKey): Many-to-one relationship with ManifestList.
    """

    architecture = models.CharField(max_length=255)
    os = models.CharField(max_length=255)
    os_version = models.CharField(max_length=255)
    os_features = models.TextField(default='', blank=True)
    features = models.TextField(default='', blank=True)
    variant = models.CharField(max_length=255)

    manifest = models.ForeignKey(
        ImageManifest, related_name='manifests', on_delete=models.CASCADE)
    manifest_list = models.ForeignKey(
        ManifestList, related_name='manifest_lists', on_delete=models.CASCADE)


class Tag(Content):
    """
    A docker tag.

    Each tag will reference either a Manifest or a ManifestList.
    A repository may contain tags with duplicate names provided each tag references
    a different type of object (Manifest|ManifestList).  This uniqueness is enforced
    programmatically.

    This content has no artifacts.

    Fields:
        name (models.CharField): The tag name.

    Relations:
        manifest (models.ForeignKey): A referenced Manifest.
        manifest_list (models.ForeignKey): A referenced ManifestList.

    """

    TYPE = 'tag'

    name = models.CharField(max_length=255, db_index=True)

    manifest = models.ForeignKey(
        ImageManifest, null=True, related_name='tags', on_delete=models.CASCADE)
    manifest_list = models.ForeignKey(
        ManifestList, null=True, related_name='tags', on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('name', 'manifest'),
            ('name', 'manifest_list'),
        )


class DockerPublisher(Publisher):
    """
    A Publisher for DockerContent.

    Define any additional fields for your new publisher if needed.
    """

    TYPE = 'docker'


class DockerRemote(Remote):
    """
    A Remote for DockerContent.

    Define any additional fields for your new importer if needed.
    """

    TYPE = 'docker'
