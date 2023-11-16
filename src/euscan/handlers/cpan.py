# Copyright 2011 Corentin Chary <corentin.chary@gmail.com>
# Copyright 2020-2023 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import json
import re
import urllib.error
import urllib.parse
import urllib.request

import portage

from euscan import helpers, mangling, output

HANDLER_NAME = "cpan"
CONFIDENCE = 100
PRIORITY = 90

_cpan_package_name_re = re.compile("mirror://cpan/authors/.*/([^/.]*).*")


def can_handle(pkg, url=None):
    return url and url.startswith("mirror://cpan/")


def guess_package(cp, url):
    match = _cpan_package_name_re.search(url)

    pkg = None

    if match:
        pkg = match.group(1)
        try:
            # Output is None if input is invalid, therefore TypeError when
            # this None is attempted to be unpacked into three variables.
            cp, ver, rev = portage.pkgsplit("fake/" + pkg)
        except TypeError:
            pass

    cat, pkg = cp.split("/")

    return pkg


def mangle_version(up_pv):
    if up_pv.startswith("v"):
        return up_pv[1:]

    # clean
    up_pv = up_pv.replace("._", "_")  # e.g.: 0.999._002 -> 0.999_002
    up_pv = up_pv.replace("_0.", "_")  # e.g.: 0.30_0.1 -> 0.30_1

    # Detect _rc versions
    rc_part = ""
    if up_pv.count("_") == 1:
        up_pv, rc_part = up_pv.split("_")

    # Gentoo creates groups of 3 digits, except for the first digit,
    # or when last digit is 0.  e.g.: 4.11 -> 4.110.0
    splitted = up_pv.split(".")

    if len(splitted) == 2:  # Split second part is sub-groups
        part = splitted.pop()
        for i in range(0, len(part), 3):
            splitted.append(part[i : i + 3])

    if len(splitted) == 2:  # add last group if it's missing
        splitted.append("0")

    groups = [splitted[0]]
    for part in splitted[1:-1]:
        groups.append(part.ljust(3, "0"))
    if splitted[-1] == "0":
        groups.append(splitted[-1])
    else:
        groups.append(splitted[-1].ljust(3, "0"))

    # if there's a group with leading zeros strip it.  e.g.: 002 -> 2
    groups = [g.lstrip("0") if g != "0" else g for g in groups]

    pv = ".".join(groups)

    if rc_part:
        pv = f"{pv}_rc{rc_part}"

    return pv


def cpan_mangle_version(pv):
    pos = pv.find(".")
    if pos <= 0:
        return pv
    up_pv = pv.replace(".", "")
    up_pv = up_pv[0:pos] + "." + up_pv[pos:]
    return up_pv


def cpan_vercmp(cp, a, b):
    try:
        return float(a) - float(b)
    except OverflowError:
        return helpers.simple_vercmp(a, b)


def scan_url(pkg, url, options):
    cp, ver, rev = portage.pkgsplit(pkg.cpv)
    remote_pkg = guess_package(cp, url)

    output.einfo("Using CPAN API: %s", remote_pkg)

    return scan_pkg(pkg, {"data": remote_pkg})


def scan_pkg(pkg, options):
    remote_pkg = options["data"]

    # Defaults to CPAN mangling rules
    if "versionmangle" not in options:
        options["versionmangle"] = ["cpan", "gentoo"]

    url = "http://search.cpan.org/api/dist/%s" % remote_pkg
    cp, ver = pkg.cp, pkg.version
    m_ver = cpan_mangle_version(ver)

    output.einfo("Using CPAN API: " + url)

    try:
        fp = helpers.urlopen(url)
    except urllib.error.URLError:
        return []
    except OSError:
        return []

    if not fp:
        return []

    data = fp.read()
    data = json.loads(data)

    if "releases" not in data:
        return []

    ret = []

    for version in data["releases"]:
        # if version['status'] == 'testing':
        #    continue

        up_pv = version["version"]
        pv = mangling.mangle_version(up_pv, options)

        if up_pv.startswith("v"):
            if helpers.version_filtered(cp, ver, pv):
                continue
        else:
            m_pv = cpan_mangle_version(up_pv)
            if helpers.version_filtered(cp, m_ver, m_pv, cpan_vercmp):
                continue

        url = f"mirror://cpan/authors/id/{version['cpanid'][0]}/{version['cpanid'][0:1]}/{version['cpanid']}/{version['archive']}"
        url = mangling.mangle_url(url, options)
        ret.append((url, pv, HANDLER_NAME, CONFIDENCE))

    return ret
