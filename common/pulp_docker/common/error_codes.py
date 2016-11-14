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
    "%(field)s may only contain lower case letters, integers, hyphens, periods, and may include "
    "a single slash. When %(field)s is not specified, the repo-id value is used. In that case the "
    "repo-id needs to adhere to the same requirements as %(field)s."),
    ['field', 'value'])
DKR1007 = Error("DKR1007", _("Could not fetch repository %(repo)s from registry %(registry)s - "
                             "%(reason)s"),
                ['repo', 'registry', 'reason'])
DKR1008 = Error("DKR1008", _("Could not find registry API at %(registry)s"), ['registry'])
DKR1009 = Error("DKR1009", _("Docker rsync distributor configuration requires a "
                             "postdistributor_id."), [])
DKR1010 = Error("DKR1010", _("Manifest with digest %(digest)s could not be "
                             "found in repository %(repo_id)s."),
                ['digest', 'repo_id'])
