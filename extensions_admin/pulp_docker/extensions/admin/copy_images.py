from gettext import gettext as _

from pulp.client.commands.unit import UnitCopyCommand

from pulp_docker.common import constants


DESC_COPY = _('copies images from one repository into another')

MODULE_ID_TEMPLATE = '%(image_id)s'


def get_formatter_for_type(type_id):
    """
    Return a method that takes one argument (a unit) and formats a short string
    to be used as the output for the unit_remove command

    :param type_id: The type of the unit for which a formatter is needed
    :type type_id: str
    :raises ValueError: if the method does not recognize the type_id
    """

    if type_id != constants.IMAGE_TYPE_ID:
        raise ValueError(_("The docker image formatter can not process %s units.") % type_id)

    return lambda x: MODULE_ID_TEMPLATE % x


class ImageCopyCommand(UnitCopyCommand):

    def __init__(self, context, name='copy', description=DESC_COPY):
        super(ImageCopyCommand, self).__init__(context, name=name, description=description,
                                               method=self.run, type_id=constants.IMAGE_TYPE_ID)

    @staticmethod
    def get_formatter_for_type(type_id):
        """
        Returns a method that can be used to format the unit key of a docker image
        for display purposes

        :param type_id: the type_id of the unit key to get a formatter for
        :type type_id: str
        :return: function
        """
        return get_formatter_for_type(type_id)
