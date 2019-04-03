from django.core.exceptions import ObjectDoesNotExist

from pulpcore.plugin.models import CreatedResource

from pulp_docker.app.models import DockerDistribution
from pulp_docker.app.serializers import DockerDistributionSerializer


def create(*args, **kwargs):
    """
    Creates a :class:`~pulp_docker.app.models.DockerDistribution`.

    Raises:
        ValidationError: If the DockerDistributionSerializer is not valid

    """
    data = kwargs.pop('data', None)
    serializer = DockerDistributionSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    resource = CreatedResource(content_object=serializer.instance)
    resource.save()


def update(instance_id, *args, **kwargs):
    """
    Updates a :class:`~pulp_docker.app.models.DockerDistribution`.

    Args:
        instance_id (int): The id of the DockerDistribution to be updated

    Raises:
        ValidationError: If the DistributionSerializer is not valid

    """
    data = kwargs.pop('data', None)
    partial = kwargs.pop('partial', False)
    instance = DockerDistribution.objects.get(pk=instance_id)
    serializer = DockerDistributionSerializer(instance, data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    serializer.save()


def delete(instance_id, *args, **kwargs):
    """
    Delete a :class:`~pulp_docker.app.models.DockerDistribution`.

    Args:
        instance_id (int): The id of the DockerDistribution to be deleted

    Raises:
        ObjectDoesNotExist: If the DockerDistribution was already deleted

    """
    try:
        instance = DockerDistribution.objects.get(pk=instance_id)
    except ObjectDoesNotExist:
        # The object was already deleted, and we don't want an error thrown trying to delete again.
        return
    else:
        instance.delete()
