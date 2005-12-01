#!/usr/bin/env python

"""Setup script for the pyparsing module distribution."""
from distutils.core import setup

from pyparsing import __version__

setup(# Distribution meta-data
    name = "pyparsing",
    version = __version__,
    description = "Python parsing module",
    author = "Paul McGuire",
    author_email = "ptmcg@users.sourceforge.net",
    url = "http://pyparsing.sourceforge.net/",
    license = "MIT License",
    py_modules = ["pyparsing"],
    )
