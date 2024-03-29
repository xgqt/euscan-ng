# Copyright 2011 Corentin Chary <corentin.chary@gmail.com>
# Copyright 2020-2024 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import json
import re
import urllib.error
import urllib.parse
import urllib.request

import portage

from euscan import helpers, mangling, output

HANDLER_NAME = "rubygems"
CONFIDENCE = 100
PRIORITY = 90


def can_handle(pkg, url=None):
    return url and url.startswith("https://rubygems.org/")


def guess_gem(cpv, url):
    match = re.search("https://rubygems.org/gems/(.*).gem", url)
    if match:
        cpv = "fake/%s" % match.group(1)

    ret = portage.pkgsplit(cpv)
    if not ret:
        return None

    cp, ver, rev = ret
    cat, pkg = cp.split("/")

    return pkg


def scan_url(pkg, url, options):
    "http://guides.rubygems.org/rubygems-org-api/#gemversion"

    gem = guess_gem(pkg.cpv, url)

    if not gem:
        output.eerror(f"Can't guess gem name using {pkg.cpv} and {url}")
        return []

    output.einfo("Using RubyGem API: %s" % gem)

    return scan_pkg(pkg, {"data": gem})


def scan_pkg(pkg, options):
    gem = options["data"]
    url = "http://rubygems.org/api/v1/versions/%s.json" % gem

    try:
        fp = helpers.urlopen(url)
    except urllib.error.URLError:
        return []
    except OSError:
        return []

    if not fp:
        return []

    data = fp.read()
    versions = json.loads(data)

    cp, ver, rev = portage.pkgsplit(pkg.cpv)

    ret = []
    for version in versions:
        up_pv = version["number"]
        pv = mangling.mangle_version(up_pv, options)
        if helpers.version_filtered(cp, ver, pv):
            continue
        url = f"http://rubygems.org/gems/{gem}-{up_pv}.gem"
        url = mangling.mangle_url(url, options)
        ret.append((url, pv, HANDLER_NAME, CONFIDENCE))
    return ret
