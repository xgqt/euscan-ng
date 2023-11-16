# Copyright 2011 Corentin Chary <corentin.chary@gmail.com>
# Copyright 2020-2023 src_prepare group
# Distributed under the terms of the GNU General Public License v2

import errno
import os
import re
import urllib
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from xml.dom.minidom import Document

import portage
from portage import dep

import euscan
from euscan import BLACKLIST_VERSIONS, CONFIG, ROBOTS_TXT_BLACKLIST_DOMAINS
from euscan.version import parse_version


def htop_vercmp(a, b):
    def fixver(v):
        if v in ["0.11", "0.12", "0.13"]:
            v = "0.1." + v[3:]
        return v

    return simple_vercmp(fixver(a), fixver(b))


VERSION_CMP_PACKAGE_QUIRKS = {"sys-process/htop": htop_vercmp}

_v_end = r"(?:(?:-|_)(?:pre|p|beta|b|alpha|a|rc|r)\d*)"
_v = r"((?:\d+)(?:(?:\.\d+)*)(?:[a-zA-Z]*?)(?:" + _v_end + "*))"


def cast_int_components(version):
    for i, obj in enumerate(version):
        try:
            version[i] = int(obj)
        except ValueError:
            pass
    return version


def simple_vercmp(a, b):
    if a == b:
        return 0

    # For sane versions
    r = portage.versions.vercmp(a, b)

    if r is not None:
        return r

    # Fallback
    a = parse_version(a)
    b = parse_version(b)

    if a < b:
        return -1
    else:
        return 1


def vercmp(package, a, b):
    if package in VERSION_CMP_PACKAGE_QUIRKS:
        return VERSION_CMP_PACKAGE_QUIRKS[package](a, b)
    return simple_vercmp(a, b)


def version_is_nightly(a, b):
    a = parse_version(a)
    b = parse_version(b)

    # Try to skip nightly builds when not wanted (www-apps/moodle)
    if len(a) != len(b) and len(b) == 2 and len(b[0]) == len("yyyymmdd"):
        if b[0][:4] != "0000":
            return True
    return False


def version_blacklisted(cp, version):
    rule = None
    cpv = "%s-%s" % (cp, version)

    # Check that the generated cpv can be used by portage
    if not portage.versions.catpkgsplit(cpv):
        return False

    for bv in BLACKLIST_VERSIONS:
        if dep.match_from_list(bv, [cpv]):
            rule = bv
            None

    if rule:
        euscan.output.einfo("%s is blacklisted by rule %s" % (cpv, rule))
    return rule is not None


def version_change_end_sep(version):
    match = re.match(r".*(%s)" % _v_end, version)
    if not match:
        return None
    end = match.group(1)
    if end[0] == "_":
        newend = end.replace("_", "-")
    elif end[0] == "-":
        newend = end.replace("-", "_")
    else:
        return None
    return version.replace(end, newend)


def version_filtered(cp, base, version, vercmp=vercmp):
    if vercmp(cp, base, version) >= 0:
        return True

    if version_blacklisted(cp, version):
        return True

    if version_is_nightly(base, version):
        return True

    return False


def generate_templates_vars(version):
    ret = []

    part = split_version(version)
    for i in range(2, len(part)):
        ver = []
        var = []
        for j in range(i):
            ver.append(str(part[j]))
            var.append("${%d}" % j)

        ret.append((".".join(ver), ".".join(var)))
    ret.append((version, "${PV}"))
    ret.reverse()
    return ret


def template_from_url(url, version):
    prefix, chunks = url.split("://")
    chunks = chunks.split("/")

    for i in range(len(chunks)):
        chunk = chunks[i]

        subs = generate_templates_vars(version)
        for sub in subs:
            chunk = chunk.replace(sub[0], sub[1])

        chunks[i] = chunk

    return prefix + "://" + "/".join(chunks)


def url_from_template(url, version):
    components = split_version(version)

    url = url.replace("${PV}", version)
    for i in range(len(components)):
        url = url.replace("${%d}" % i, str(components[i]))

    return url


# Stolen from distutils.LooseVersion
# Used for brute force to increment the version
def split_version(version):
    component_re = re.compile(r"(\d+ | [a-z]+ | \.)", re.VERBOSE)
    components = [x for x in component_re.split(version) if x and x != "."]
    for i in range(len(components)):
        try:
            components[i] = int(components[i])
        except ValueError:
            pass
    return components


def join_version(components):
    version = ""
    for i in range(len(components)):
        version += str(components[i])
        if i >= len(components) - 1:
            break
        if not isinstance(components[i], str) and not isinstance(
            components[i + 1], str
        ):
            version += "."
    return version


def increment_version(components, level):
    n = len(components)

    if level > n - 1 or level < 0:
        raise Exception

    for i in range(n, level + 1, -1):
        if isinstance(components[i - 1], int):
            components[i - 1] = 0

    if isinstance(components[level], int):
        components[level] += 1

    return components


def gen_versions(components, level):
    n = len(components)
    depth = level
    level = min(level, n)

    if not n:
        return []

    versions = []

    for i in range(n, n - level, -1):
        increment_version(components, i - 1)
        for j in range(depth):
            versions.append(list(components))
            increment_version(components, i - 1)

    return versions


def timeout_for_url(url):
    if "sourceforge" in url:
        timeout = 15
    else:
        timeout = 5
    return timeout


class HeadRequest(urllib.request.Request):
    def get_method(self):
        return "HEAD"


# RobotParser cache
rpcache = {}


def urlallowed(url):
    if CONFIG["skip-robots-txt"]:
        return True

    protocol, domain = urllib.parse.urlparse(url)[:2]

    for bd in ROBOTS_TXT_BLACKLIST_DOMAINS:
        if re.match(bd, domain):
            return True

    for d in ["sourceforge", "berlios", "github.com"]:
        if d in domain:
            return True

    if protocol == "ftp":
        return True

    baseurl = "%s://%s" % (protocol, domain)
    robotsurl = urllib.parse.urljoin(baseurl, "robots.txt")

    if baseurl in rpcache:
        rp = rpcache[baseurl]
    else:
        from socket import getdefaulttimeout, setdefaulttimeout

        timeout = getdefaulttimeout()
        setdefaulttimeout(5)

        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robotsurl)
        try:
            rp.read()
            rpcache[baseurl] = rp
        except IOError:
            rp = None

        setdefaulttimeout(timeout)

    return rp.can_fetch(CONFIG["user-agent"], url) if rp else True


def urlopen(url, timeout=None, verb="GET"):
    if not urlallowed(url):
        euscan.output.einfo("Url '%s' blocked by robots.txt" % url)
        return None

    if not timeout:
        timeout = timeout_for_url(url)

    if verb == "GET":
        request = urllib.request.Request(url)
    elif verb == "HEAD":
        request = HeadRequest(url)
    else:
        return None

    request.add_header("User-Agent", CONFIG["user-agent"])

    handlers = []

    if CONFIG["cache"]:
        from cache import CacheHandler

        handlers.append(CacheHandler(CONFIG["cache"]))

    if CONFIG["verbose"]:
        debuglevel = CONFIG["verbose"] - 1
        handlers.append(urllib.request.HTTPHandler(debuglevel=debuglevel))

    opener = urllib.request.build_opener(*handlers)

    return opener.open(request, None, timeout)


def tryurl(fileurl, template):
    result = True

    if not urlallowed(fileurl):
        euscan.output.einfo("Url '%s' blocked by robots.txt" % fileurl)
        return None

    euscan.output.ebegin("Trying: " + fileurl)

    try:
        basename = os.path.basename(fileurl)

        fp = urlopen(fileurl, verb="HEAD")
        if not fp:
            euscan.output.eend(errno.EPERM)
            return None

        headers = fp.info()

        # Some URLs return Content-disposition with different filename
        # Disable check for now (I have no seen false positives)
        # if 'Content-disposition' in headers and \
        #   basename not in headers['Content-disposition']:
        #    result = None
        if "Content-Length" in headers and headers["Content-Length"] == "0":
            result = None
        elif "Content-Type" in headers and "text/html" in headers["Content-Type"]:
            result = None
        elif (
            "Content-Type" in headers
            and "application/x-httpd-php" in headers["Content-Type"]
        ):
            result = None
        elif fp.geturl() != fileurl:
            regex = regex_from_template(template)
            baseregex = regex_from_template(os.path.basename(template))
            basename2 = os.path.basename(fp.geturl())

            # Redirect to another (earlier?) version
            if basename != basename2 and (
                re.match(regex, fp.geturl()) or re.match(baseregex, basename2)
            ):
                result = None

            if result:
                result = (fp.geturl(), fp.info())

    except urllib.error.URLError:
        result = None
    except IOError:
        result = None

    euscan.output.eend(errno.ENOENT if not result else 0)

    return result


def regex_from_template(template):
    # Escape
    regexp = re.escape(template)

    # Unescape specific stuff
    regexp = regexp.replace(r"\$\{", "${")
    regexp = regexp.replace(r"\}", "}")
    regexp = regexp.replace(r"}\.$", "}.$")

    # Replace ${\d+}
    # regexp = regexp.replace('${0}', r'([\d]+?)')
    regexp = re.sub(r"(\$\{\d+\}(\.?))+", r"([\\w\.]+?)", regexp)

    # regexp = re.sub(r'(\$\{\d+\}\.?)+', r'([\w]+?)', regexp)
    # regexp = re.sub(r'(\$\{\d+\}\.+)+', '(.+?)\.', regexp)
    # regexp = re.sub(r'(\$\{\d+\})+', '(.+?)', regexp)

    # Full version
    regexp = regexp.replace("${PV}", _v)

    # End
    regexp = regexp + r"/?$"

    return regexp


def basedir_from_template(template):
    idx = template.find("${")
    if idx == -1:
        return template

    idx = template[0:idx].rfind("/")
    if idx == -1:
        return ""

    return template[0:idx]


def generate_scan_paths(url):
    prefix, chunks = url.split("://")
    chunks = chunks.split("/")

    steps = []

    path = prefix + ":/"
    for chunk in chunks:
        if "${" in chunk:
            steps.append((path, "^(?:|.*/)" + regex_from_template(chunk)))
            path = ""
        else:
            path += "/"
            path += chunk

    return steps


def parse_mirror(uri):
    from random import shuffle

    mirrors = portage.settings.thirdpartymirrors()

    if not uri.startswith("mirror://"):
        return uri

    eidx = uri.find("/", 9)
    if eidx == -1:
        euscan.output.einfo("Invalid mirror definition in SRC_URI:\n")
        euscan.output.einfo("  %s\n" % (uri))
        return None

    mirrorname = uri[9:eidx]
    path = uri[eidx + 1 :]

    if mirrorname in mirrors:
        mirrors = mirrors[mirrorname]
        shuffle(mirrors)
        uri = mirrors[0].strip("/") + "/" + path
    else:
        euscan.output.einfo("No known mirror by the name: %s" % (mirrorname))
        return None

    return uri


def dict_to_xml(data, indent):
    doc = Document()
    root = doc.createElement("euscan")
    doc.appendChild(root)

    def _set_value(parent, value):
        if isinstance(value, dict):
            for k, v in list(value.items()):
                node = doc.createElement(k)
                _set_value(node, v)
                parent.appendChild(node)
        elif isinstance(value, list):
            for item in value:
                node = doc.createElement("value")
                text = doc.createTextNode(item)
                node.appendChild(text)
                parent.appendChild(node)
        else:
            text = doc.createTextNode(str(value))
            parent.appendChild(text)

    for key, value in list(data.items()):
        node = doc.createElement("package")
        node.setAttribute("name", key)
        _set_value(node, value)
        root.appendChild(node)

    return doc.toprettyxml(indent=" " * indent)
