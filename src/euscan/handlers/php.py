# Copyright 2011 Corentin Chary <corentin.chary@gmail.com>
# Copyright 2020-2023 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import re
import urllib.error
import urllib.parse
import urllib.request
import xml.dom.minidom

from euscan import helpers, mangling, output

HANDLER_NAME = "php"
CONFIDENCE = 100
PRIORITY = 90


def can_handle(pkg, url=None):
    return False


def guess_package_and_channel(cp, url):
    match = re.search(r"http://(.*)\.php\.net/get/(.*)-(.*).tgz", url)

    if match:
        host = match.group(1)
        pkg = match.group(2)
    else:
        cat, pkg = cp.split("/")

    return pkg, host


def scan_url(pkg, url, options):
    package, channel = guess_package_and_channel(pkg.cp, url)
    return scan_pkg(pkg, {"type": channel, "data": package})


def scan_pkg(pkg, options):
    cp, ver = pkg.cp, pkg.version

    package = options["data"]
    channel = options["type"]

    url = f"http://{channel}.php.net/rest/r/{package.lower()}/allreleases.xml"

    output.einfo("Using: " + url)

    try:
        fp = helpers.urlopen(url)
    except urllib.error.URLError:
        return []
    except OSError:
        return []

    if not fp:
        return []

    data = fp.read()

    dom = xml.dom.minidom.parseString(data)

    nodes = dom.getElementsByTagName("v")
    ret = []

    for node in nodes:
        up_pv = node.childNodes[0].data
        pv = mangling.mangle_version(up_pv, options)
        if helpers.version_filtered(cp, ver, pv):
            continue

        url = f"http://{channel}.php.net/get/{package}-{up_pv}.tgz"
        url = mangling.mangle_url(url, options)

        ret.append((url, pv, HANDLER_NAME, CONFIDENCE))

    return ret
