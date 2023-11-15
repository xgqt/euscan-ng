import re
import urllib.error
import urllib.parse
import urllib.request

import portage

from euscan import output
from euscan.handlers.url import process_scan as url_scan
from euscan.helpers import regex_from_template

HANDLER_NAME = "berlios"
CONFIDENCE = 90
PRIORITY = 90


berlios_regex = r"mirror://berlios/([^/]+)/([^/]+)"


def can_handle(pkg, url=None):
    if not url:
        return False

    cp, ver, rev = portage.pkgsplit(pkg.cpv)
    if ver not in url:
        return False

    return re.search(berlios_regex, url)


def scan_url(pkg, url, options):
    output.einfo("Using BerliOS handler")

    cp, ver, rev = portage.pkgsplit(pkg.cpv)

    project, filename = re.search(berlios_regex, url).groups()

    project_page = "http://developer.berlios.de/projects/%s" % project
    content = urllib.request.urlopen(project_page).read()

    project_id = re.search(r"/project/filelist.php\?group_id=(\d+)", content).group(1)

    base_url = (
        "http://developer.berlios.de/project/filelist.php?group_id=%s" % project_id
    )

    file_pattern = regex_from_template(filename.replace(ver, "${PV}"))

    result = url_scan(pkg, base_url, file_pattern)

    ret = []
    for found_url, pv, _, _ in result:
        found_url = found_url.replace("prdownload", "download")
        ret.append((found_url, pv, HANDLER_NAME, CONFIDENCE))
    return ret
