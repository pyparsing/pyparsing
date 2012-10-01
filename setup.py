#!/usr/bin/env python

"""Setup script for the pyparsing module distribution."""
from distutils.core import setup

import sys
import os

_PY3 = sys.version_info[0] > 2

if _PY3:
    from pyparsing_py3 import __version__ as pyparsing_version
else:
    from pyparsing_py2 import __version__ as pyparsing_version
    
modules = ["pyparsing",]

# make sure that a pyparsing.py file exists - if not, copy the appropriate version
def fileexists(fname):
    try:
        return bool(os.stat(fname))
    except:
        return False

def copyfile(fromname, toname):
    outf = open(toname,'w')
    outf.write(open(fromname).read())
    outf.close()
    
if "MAKING_PYPARSING_RELEASE" not in os.environ and not fileexists("pyparsing.py"):
    if _PY3:
        from_file = "pyparsing_py3.py"
    else:
        from_file = "pyparsing_py2.py"
    copyfile(from_file, "pyparsing.py")

setup(# Distribution meta-data
    name = "pyparsing",
    version = pyparsing_version,
    description = "Python parsing module",
    author = "Paul McGuire",
    author_email = "ptmcg@users.sourceforge.net",
    url = "http://pyparsing.wikispaces.com/",
    download_url = "http://sourceforge.net/project/showfiles.php?group_id=97203",
    license = "MIT License",
    py_modules = modules,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        ]
    )
