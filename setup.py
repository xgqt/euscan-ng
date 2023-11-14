#!/usr/bin/env python
from setuptools import setup, Command

import io
import os
import re


__version__ = os.getenv('VERSION', default='9999')

cwd = os.getcwd()

# Load EPREFIX from Portage, fall back to the empty string if it fails
try:
    from portage.const import EPREFIX
except ImportError:
    EPREFIX = ''

# Python files that need `__version__ = ""` subbed, relative to this dir:
python_scripts = [os.path.join(cwd, path) for path in (
    'bin/euscan',
)]


class SetVersion(Command):
    """Set python __version__ to our __version__."""
    description = "hardcode scripts' version using VERSION from environment"
    user_options = []  # [(long_name, short_name, desc),]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        ver = 'git' if __version__ == '9999' else __version__
        print(("Settings version to %s" % ver))

        def sub(files, pattern):
            for f in files:
                updated_file = []
                with io.open(f, 'r', 1, 'utf_8') as s:
                    for line in s:
                        newline = re.sub(pattern, '"%s"' % ver, line, 1)
                        if newline != line:
                            log.info("%s: %s" % (f, newline))
                        updated_file.append(newline)
                with io.open(f, 'w', 1, 'utf_8') as s:
                    s.writelines(updated_file)
        quote = r'[\'"]{1}'
        python_re = r'(?<=^__version__ = )' + quote + '[^\'"]*' + quote
        sub(python_scripts, python_re)

setup(
    version=__version__,
    cmdclass={
        'set_version': SetVersion,
    },
)
