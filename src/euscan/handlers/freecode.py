# Copyright 2011 Corentin Chary <corentin.chary@gmail.com>
# Copyright 2020-2023 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import re
import urllib.error
import urllib.parse
import urllib.request

import portage

from euscan import helpers, mangling, output

HANDLER_NAME = "freecode"
CONFIDENCE = 100
PRIORITY = 90


def can_handle(pkg, url=None):
    return False


def scan_pkg(pkg, options):
    cp, ver, rev = portage.pkgsplit(pkg.cpv)

    package = options["data"].strip()

    output.einfo("Using FreeCode handler: " + package)

    fp = urllib.request.urlopen("http://freecode.com/projects/%s/releases" % package)
    content = str(fp.read())

    result = re.findall(
        r'<a href="/projects/%s/releases/(\d+)">([^<]+)</a>' % package, content
    )

    ret = []
    for release_id, up_pv in result:
        pv = mangling.mangle_version(up_pv, options)
        if helpers.version_filtered(cp, ver, pv):
            continue
        fp = urllib.request.urlopen(
            "http://freecode.com/projects/%s/releases/%s" % (package, release_id)
        )
        content = str(fp.read())
        download_page = re.findall(r'<a href="(/urls/[^"]+)"', content)[0]
        fp = urllib.request.urlopen("http://freecode.com%s" % download_page)
        content = str(fp.read())
        url = re.findall(
            r'In case it doesn\'t, click here: <a href="([^"]+)"', content
        )[0]
        ret.append((url, pv, HANDLER_NAME, CONFIDENCE))
    return ret
