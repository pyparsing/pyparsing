#!/usr/bin/env python

"""Setup script for the pyparsing module distribution."""
from distutils.core import setup

import sys
import os

from pyparsing import __version__ as pyparsing_version

modules = ["pyparsing",]

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
        ],
    )
