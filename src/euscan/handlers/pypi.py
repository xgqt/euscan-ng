# Copyright 2011 Corentin Chary <corentin.chary@gmail.com>
# Copyright 2020-2023 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import re
import xmlrpc.client

import portage

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
    "http://wiki.python.org/moin/PyPiXmlRpc"

    package = guess_package(pkg.cpv, url)
    return scan_pkg(pkg, {"data": package})


def scan_pkg(pkg, options):
    package = options["data"]

    output.einfo("Using PyPi XMLRPC: " + package)

    client = xmlrpc.client.ServerProxy("https://pypi.python.org/pypi")
    versions = client.package_releases(package)

    if not versions:
        return versions

    versions.reverse()

    cp, ver, rev = portage.pkgsplit(pkg.cpv)

    ret = []
    for up_pv in versions:
        pv = mangling.mangle_version(up_pv, options)
        if helpers.version_filtered(cp, ver, pv):
            continue
        urls = client.release_urls(package, up_pv)
        urls = " ".join([mangling.mangle_url(infos["url"], options) for infos in urls])
        ret.append((urls, pv, HANDLER_NAME, CONFIDENCE))
    return ret
