from gettext import gettext as _

from pulp.client.commands import options
from pulp.client.commands.criteria import DisplayUnitAssociationsCommand
from pulp.client.commands.unit import UnitCopyCommand, UnitRemoveCommand

from pulp_docker.common import constants


DESC_COPY_MANIFESTS = _('copies manifests from one repository into another')
DESC_COPY_TAGS = _('copies tags from one repository into another')
DESC_REMOVE_MANIFESTS = _('remove manifests from a repository')
DESC_REMOVE_TAGS = _('remove tags from a repository')
DESC_SEARCH_MANIFESTS = _('search for manifests in a repository')
DESC_SEARCH_TAGS = _('search for tags in a repository')
FORMAT_ERR = _('The docker formatter can not process %s units.')

MANIFEST_AND_BLOB_TEMPLATE = '%(digest)s'
TAG_TEMPLATE = '%(name)s'


def get_formatter_for_type(type_id):
    """
    Returns a formatter that can be used to format the unit key
    of a docker tag, manifest, or blob for display purposes.

    :param type_id: A unit type ID.
    :type type_id: str
    :return: A formatter.
    :rtype: callable
    :raises ValueError: when the type_id is not supported.
    """
    if type_id == constants.TAG_TYPE_ID:
        return lambda u: TAG_TEMPLATE % u
    elif type_id in [constants.MANIFEST_TYPE_ID, constants.BLOB_TYPE_ID]:
        return lambda u: MANIFEST_AND_BLOB_TEMPLATE % u
    else:
        raise ValueError(FORMAT_ERR % type_id)


class TagSearchCommand(DisplayUnitAssociationsCommand):
    """
    Command used to search for tag units in a repository.
    """

    def __init__(self, context):
        """
        :param context: A client context.
        :type  context: pulp.client.extensions.core.ClientContext
        """
        super(TagSearchCommand, self).__init__(
            name='tag',
            description=DESC_SEARCH_TAGS,
            method=self.run)
        self.context = context
        self.prompt = context.prompt

    def run(self, **kwargs):
        """
        Print a list of all the tags matching the search parameters.

        :param kwargs: the search parameters for finding docker tags
        :type kwargs: dict
        """
        repo_id = kwargs.pop(options.OPTION_REPO_ID.keyword)
        kwargs['type_ids'] = [constants.TAG_TYPE_ID]
        reply = self.context.server.repo_unit.search(repo_id, **kwargs)
        tags = reply.response_body
        self.prompt.render_document_list(tags)


class TagCopyCommand(UnitCopyCommand):
    """
    Command used to copy tag units between repositories.
    """

    def __init__(self, context):
        """
        :param context: A client context.
        :type  context: pulp.client.extensions.core.ClientContext
        """
        super(TagCopyCommand, self).__init__(
            context,
            name='tag',
            description=DESC_COPY_TAGS,
            method=self.run,
            type_id=constants.TAG_TYPE_ID)

    def get_formatter_for_type(self, type_id):
        """
        Returns a formatter that can be used to format the unit key
        of a docker tag or blob for display purposes.

        :param type_id: A unit type ID.
        :type type_id: str
        :return: A formatter.
        :rtype: callable
        :raises ValueError: when the type_id is not supported.
        """
        return get_formatter_for_type(type_id)


class TagRemoveCommand(UnitRemoveCommand):
    """
    Command used to remove tag units from a repository.
    """

    def __init__(self, context):
        """
        :param context: A client context.
        :type  context: pulp.client.extensions.core.ClientContext
        """
        super(TagRemoveCommand, self).__init__(
            name='tag',
            description=DESC_REMOVE_TAGS,
            context=context,
            method=self.run,
            type_id=constants.TAG_TYPE_ID)

    def get_formatter_for_type(self, type_id):
        """
        Returns a formatter that can be used to format the unit key
        of a docker tag or blob for display purposes.

        :param type_id: A unit type ID.
        :type type_id: str
        :return: A formatter.
        :rtype: callable
        :raises ValueError: when the type_id is not supported.
        """
        return get_formatter_for_type(type_id)


class ManifestSearchCommand(DisplayUnitAssociationsCommand):
    """
    Command used to search for manifest units in a repository.
    """

    def __init__(self, context):
        """
        :param context: A client context.
        :type  context: pulp.client.extensions.core.ClientContext
        """
        super(ManifestSearchCommand, self).__init__(
            name='manifest',
            description=DESC_SEARCH_MANIFESTS,
            method=self.run)
        self.context = context
        self.prompt = context.prompt

    def run(self, **kwargs):
        """
        Print a list of all the manifests matching the search parameters.

        :param kwargs: the search parameters for finding docker manifests
        :type kwargs: dict
        """
        repo_id = kwargs.pop(options.OPTION_REPO_ID.keyword)
        kwargs['type_ids'] = [constants.MANIFEST_TYPE_ID]
        reply = self.context.server.repo_unit.search(repo_id, **kwargs)
        manifests = reply.response_body
        self.prompt.render_document_list(manifests)


class ManifestCopyCommand(UnitCopyCommand):
    """
    Command used to copy manifest units between repositories.
    """

    def __init__(self, context):
        """
        :param context: A client context.
        :type  context: pulp.client.extensions.core.ClientContext
        """
        super(ManifestCopyCommand, self).__init__(
            context,
            name='manifest',
            description=DESC_COPY_MANIFESTS,
            method=self.run,
            type_id=constants.MANIFEST_TYPE_ID)

    def get_formatter_for_type(self, type_id):
        """
        Returns a formatter that can be used to format the unit key
        of a docker manifest or blob for display purposes.

        :param type_id: A unit type ID.
        :type type_id: str
        :return: A formatter.
        :rtype: callable
        :raises ValueError: when the type_id is not supported.
        """
        return get_formatter_for_type(type_id)


class ManifestRemoveCommand(UnitRemoveCommand):
    """
    Command used to remove manifest units from a repository.
    """

    def __init__(self, context):
        """
        :param context: A client context.
        :type  context: pulp.client.extensions.core.ClientContext
        """
        super(ManifestRemoveCommand, self).__init__(
            name='manifest',
            description=DESC_REMOVE_MANIFESTS,
            context=context,
            method=self.run,
            type_id=constants.MANIFEST_TYPE_ID)

    def get_formatter_for_type(self, type_id):
        """
        Returns a formatter that can be used to format the unit key
        of a docker manifest or blob for display purposes.

        :param type_id: A unit type ID.
        :type type_id: str
        :return: A formatter.
        :rtype: callable
        :raises ValueError: when the type_id is not supported.
        """
        return get_formatter_for_type(type_id)
