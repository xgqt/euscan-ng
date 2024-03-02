# Copyright 2011 Corentin Chary <corentin.chary@gmail.com>
# Copyright 2020-2024 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import json
import re
import urllib.error

import portage
from packaging.version import parse

from euscan import helpers, mangling, output

HANDLER_NAME = "pypi"
CONFIDENCE = 100
PRIORITY = 90


def can_handle(pkg, url=None):
    return url and url.startswith("mirror://pypi/")


def guess_package(cp, url):
    match = re.search(r"mirror://pypi/\w+/(.*)/.*", url)
    if match:
        return match.group(1)

    cat, pkg = cp.split("/")

    return pkg


def scan_url(pkg, url, options):
    "https://peps.python.org/pep-0691/"

    package = guess_package(pkg.cpv, url)
    return scan_pkg(pkg, {"data": package})


def scan_pkg(pkg, options):
    package = options["data"]

    output.einfo("Using PyPi JSON API: " + package)

    try:
        fp = helpers.urlopen(f"https://pypi.org/pypi/{package}/json/")
    except urllib.error.URLError:
        return []
    except OSError:
        return []

    if not fp:
        return []

    data = json.loads(fp.read())

    versions = list(data["releases"].keys())

    versions.sort(key=parse, reverse=True)

    cp, ver, rev = portage.pkgsplit(pkg.cpv)

    ret = []
    for up_pv in versions:
        pv = mangling.mangle_version(up_pv, options)
        if helpers.version_filtered(cp, ver, pv):
            continue
        urls = " ".join(
            [
                mangling.mangle_url(file["url"], options)
                for file in data["releases"][up_pv]
                if file["packagetype"] == "sdist"
            ]
        )
        ret.append((urls, pv, HANDLER_NAME, CONFIDENCE))
    return ret
