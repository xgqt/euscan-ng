# Copyright 2011 Corentin Chary <corentin.chary@gmail.com>
# Copyright 2020-2023 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import configparser
import os
from ast import literal_eval

CONFIG = {
    "nocolor": False,
    "quiet": False,
    "verbose": 1,
    "debug": False,
    "brute-force": 3,
    "brute-force-recursive": True,
    "brute-force-false-watermark": 50,
    "scan-dir": True,
    "oneshot": True,
    "user-agent": "euscan-ng (https://gitlab.com/src_prepare/euscan-ng)",
    "skip-robots-txt": False,
    "cache": False,
    "format": None,
    "indent": 2,
    "progress": False,
    "mirror": False,
    "ignore-pre-release": False,
    "ignore-pre-release-if-stable": False,
    "ebuild-uri": False,
    "handlers-exclude": [],
}

config = configparser.ConfigParser()
config.read(["/etc/euscan.conf", os.path.expanduser("~/.euscan.conf")])
if config.has_section("euscan"):
    for key, value in config.items("euscan"):
        if key in CONFIG:
            CONFIG[key] = literal_eval(value)

BLACKLIST_VERSIONS = [
    # Compatibility package for running binaries linked against a
    # pre gcc 3.4 libstdc++, won't be updated
    ">=sys-libs/libstdc++-v3-3.4",
    # Actually older or incorrect
    "~app-backup/backup-manager-0.7.15",
    "=x11-plugins/wmacpimon-001",
]

BLACKLIST_PACKAGES = [
    # These kernels are almost dead
    "sys-kernel/xbox-sources",
]

SCANDIR_BLACKLIST_URLS = [
    "https://rubygems.org/(.*)",  # Not browsable
    "mirror://gentoo/(.*)",  # Directory too big
    "https://dev.gentoo.org/(.*)",  # There shouldn't be releases here
    # Waste of time to go through
    "https://crates.io/(.*)",
    "https://api.nuget.org/(.*)",
    "https://myget.org/(.*)",
]

BRUTEFORCE_BLACKLIST_PACKAGES = [
    # infinite loop any
    # http://plone.org/products/plonepopoll/releases/*/plonepopoll-2-6-1.tgz
    # link will work
    "net-zope/plonepopoll"
]

BRUTEFORCE_BLACKLIST_URLS = [
    "http://hydra.nixos.org/build/(.*)",  # infinite loop
    # Doesn't respect 404, infinite loop
    "http://www.rennings.net/gentoo/distfiles/(.*)",
    "http://art.gnome.org/download/(.*)",
    "http://barelysufficient.org/~olemarkus/(.*)",
    "http://olemarkus.org/~olemarkus/(.*)",
]

ROBOTS_TXT_BLACKLIST_DOMAINS = [
    "(.*)sourceforge(.*)",
    "(.*)github.com",
    r"(.*)qt\.nokia\.com(.*)",
    r"(.*)chromium\.org(.*)",
    r"(.*)nodejs\.org(.*)",
    r"(.*)download\.mono-project\.com(.*)",
    r"(.*)fedorahosted\.org(.*)",
    r"(.*)download\.tuxfamily\.org(.*)",
    r"(.*)festvox\.org(.*)",
]

from euscan.out import EuscanOutput  # noqa: E402

output = EuscanOutput(CONFIG)
