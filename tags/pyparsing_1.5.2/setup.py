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
    url = "http://pyparsing.wikispaces.com/",
    download_url = "http://sourceforge.net/project/showfiles.php?group_id=97203",
    license = "MIT License",
    py_modules = ["pyparsing"],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        ]
    )
