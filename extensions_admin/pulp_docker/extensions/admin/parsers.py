from gettext import gettext as _


def parse_colon_separated(input_value):
    """
    Parses a colon separated key value pair.
    The given value will actually be a list of values regardless
    of whether or not the user specified multiple notes.

    :param input_value: list of user entered values or empty list if unspecified
    :type  input_value: list
    :return: list of tuples (tag_name, image_hash)
    :rtype: list of (str, str)
    :raises ValueError: if the value can not be parsed
    """
    if input_value:
        ret = [x.rsplit(':', 1) for x in input_value]
        for value in ret:
            msg = _('Unable to parse %s, value should be in the format "aaa:bbb"')
            if len(value) != 2:
                raise ValueError(msg % value)
            elif not len(value[0]) or not len(value[1]):
                raise ValueError(msg % value)
        return ret
    else:
        return []
