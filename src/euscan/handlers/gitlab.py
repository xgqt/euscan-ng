# Copyright 2020-2024 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import json
import re

import portage

from euscan import helpers, mangling, output

HANDLER_NAME = "gitlab"
CONFIDENCE = 100
PRIORITY = 90

_gitlab_instances = [
    "gitlab.com",
    "gitlab.freedesktop.org",
    "invent.kde.org/",
    "gitlab.gnome.org",
    "gitlab.kitware.com",
    "gitlab.xfce.org",
    "code.videolan.org",
    "gitlab.xiph.org",
]

gitlab_patterns = [
    # Regular expression adapted from pkgcheck
    # https://docs.gitlab.com/ee/user/reserved_names.html
    re.compile(
        rf"https://(?P<domain>{domain})/(?P<repository>((?!api/)\w[^/]*/)+(?!raw/)\w[^/]*)"
    )
    for domain in _gitlab_instances
]


def can_handle(pkg, url=None):
    return url and any([re.search(pattern, url) for pattern in gitlab_patterns])


def scan_url(pkg, url, options):
    "https://docs.gitlab.com/ee/api/releases/index.html"

    match = [
        re.search(pattern, url)
        for pattern in gitlab_patterns
        if re.search(pattern, url) is not None
    ][0]

    domain = match.group("domain")
    repository = match.group("repository")

    output.einfo(f"Using GitLab REST API in {domain}: {repository}")

    request = helpers.urlopen(
        f"https://{domain}/api/v4/projects/{repository.replace('/', '%2F')}/releases"
    )

    data = json.load(request)

    versions = [release["tag_name"] for release in data]

    cp, ver, rev = portage.pkgsplit(pkg.cpv)

    ret = []
    for up_pv in versions:
        pv = mangling.mangle_version(up_pv, options)
        if helpers.version_filtered(cp, ver, pv):
            continue
        urls = " ".join(
            [
                mangling.mangle_url(source["url"], options)
                for source in [
                    release["assets"]["sources"]
                    for release in data
                    if release["tag_name"] == up_pv
                ][0]
                # prefer tar.bz2
                if source["format"] == "tar.bz2"
            ]
        )
        ret.append((urls, pv, HANDLER_NAME, CONFIDENCE))
    return ret
