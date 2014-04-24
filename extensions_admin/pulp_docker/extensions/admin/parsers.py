

def parse_colon_separated(input):
    """
    Parses a colon separated key value pair.
    The given value will actually be a list of values regardless
    of whether or not the user specified multiple notes.

    :param input: list of user entered values or empty list if unspecified
    :type  input: list
    :return: list of tuples (tag_name, image_hash)
    :rtype: list of (str, str)
    """
    if input:
        ret = [x.split(':', 1) for x in input]
        for value in ret:
            if len(value) != 2:
                raise ValueError
            elif not len(value[0]) or not len(value[1]):
                raise ValueError
        return ret
    else:
        return []
