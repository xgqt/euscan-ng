# Copyright 2020-2024 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import json
import re

import portage

from euscan import helpers, mangling, output

HANDLER_NAME = "gitea"
CONFIDENCE = 100
PRIORITY = 90

# Forgejo strives to be compatible with Gitea API
# https://forgejo.org/2024-02-forking-forward/

_gitea_instances = [
    "codeberg.org",
    "git.osgeo.org",
    "gitea.com",
    "gitea.ladish.org",
    "gitea.osmocom.org",
    "gitea.treehouse.systems",
]

gitea_patterns = [
    re.compile(rf"https://(?P<domain>{domain})/(?P<repository>[^/]+/[^/]+)")
    for domain in _gitea_instances
]


def can_handle(pkg, url=None):
    return url and any([re.search(pattern, url) for pattern in gitea_patterns])


def scan_url(pkg, url, options):
    "https://docs.gitea.com/api/1.20/#tag/repository/operation/repoListReleases"

    match = [
        re.search(pattern, url)
        for pattern in gitea_patterns
        if re.search(pattern, url) is not None
    ][0]

    domain = match.group("domain")
    repository = match.group("repository")

    output.einfo(f"Using Gitea API in {domain}: {repository}")

    request = helpers.urlopen(f"https://{domain}/api/v1/repos/{repository}/releases")

    data = json.load(request)

    versions = [release["tag_name"] for release in data]

    cp, ver, rev = portage.pkgsplit(pkg.cpv)

    ret = []
    for up_pv in versions:
        pv = mangling.mangle_version(up_pv, options)
        if helpers.version_filtered(cp, ver, pv):
            continue
        urls = " ".join(
            mangling.mangle_url(release["tarball_url"], options)
            for release in data
            if release["tag_name"] == up_pv
        )
        ret.append((urls, pv, HANDLER_NAME, CONFIDENCE))
    return ret
