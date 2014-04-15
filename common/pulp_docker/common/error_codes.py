from gettext import gettext as _

from pulp.common.error_codes import Error

DKR1001 = Error("DKR1001", _("The url specified for %(field) is missing a scheme. "
                             "The value specified is '%(url)'."), ['field', 'url'])
DKR1002 = Error("DKR1002", _("The url specified for %(field) is missing a hostname. "
                             "The value specified is '%(url)'."), ['field', 'url'])
DKR1003 = Error("DKR1003", _("The url specified for %(field) is missing a path. "
                             "The value specified is '%(url)'."), ['field', 'url'])
DKR1004 = Error("DKR1004", _("The value specified for %(field): '%(value)s' is not boolean."),
                ['field', 'value'])
