# Copyright 2011 Corentin Chary <corentin.chary@gmail.com>
# Copyright 2020-2023 src_prepare group
# Distributed under the terms of the GNU General Public License v2

from euscan.handlers import generic

PRIORITY = 90

HANDLER_NAME = "kde"


def can_handle(pkg, url):
    return url and url.startswith("mirror://kde/")


def clean_results(results):
    ret = []

    for path, version, _, confidence in results:
        if version == "5SUMS":
            continue
        ret.append((path, version, HANDLER_NAME, confidence))

    return ret


def scan_url(pkg, url, options):
    results = generic.scan_url(pkg, url, options)

    if url.startswith("mirror://kde/unstable/"):
        url = url.replace("mirror://kde/unstable/", "mirror://kde/stable/")
        results += generic.scan_url(pkg, url, options)

    if not results:  # if nothing was found go brute forcing
        results = generic.brute_force(pkg.cpv, url)

        if url.startswith("mirror://kde/unstable/"):
            url = url.replace("mirror://kde/unstable/", "mirror://kde/stable/")
            results += generic.brute_force(pkg.cpv, url)

    return clean_results(results)
