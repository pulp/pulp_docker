from gettext import gettext as _

from pulp.common.error_codes import Error

DKR1001 = Error("DKR1001", _("The url specified for %(field) is missing a scheme. "
                             "The value specified is '%(url)'."), ['field', 'url'])
DKR1002 = Error("DKR1002", _("The url specified for %(field) is missing a hostname. "
                             "The value specified is '%(url)'."), ['field', 'url'])
DKR1003 = Error("DKR1003", _("The url specified for %(field) is missing a path. "
                             "The value specified is '%(url)'."), ['field', 'url'])
DKR1004 = Error("DKR1004", _("The value specified for %(field)s: '%(value)s' is not boolean."),
                ['field', 'value'])
DKR1005 = Error("DKR1005", _(
    "The value specified for %(field)s: '%(value)s' is invalid. Registry id must contain only "
    "lower case letters, integers, hyphens, periods, and may include a single slash."),
    ['field', 'value'])
DKR1006 = Error("DKR1006", _(
    "If %(field)s is not specified, it will default to the id must contain only lower case letters,"
    " integers, hyphens, periods, and may include a single slash. Please specify a valid registry "
    "id or change the repo id."),
    ['field', 'value'])
DKR1007 = Error("DKR1007", _("Could not fetch repository %(repo)s from registry %(registry)s"),
                ['repo', 'registry'])
