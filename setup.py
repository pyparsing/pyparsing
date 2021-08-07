#!/usr/bin/env python

"""Setup script for the pyparsing module distribution."""

from setuptools import setup
import io
import sys
from pyparsing import __version__ as pyparsing_version

# guard against manual invocation of setup.py (when using pip, we shouldn't even get this far)
if sys.version_info[:2] < (3, 6):
    sys.exit(
        "Python < 3.6 is not supported in this version of pyparsing; use latest pyparsing 2.4.x release"
    )

# get the text of the README file
README_name = __file__.replace("setup.py", "README.rst")
with io.open(README_name, encoding="utf8") as README:
    pyparsing_main_doc = README.read()

packages = ["pyparsing", "pyparsing.diagram"]

setup(  # Distribution meta-data
    name="pyparsing",
    version=pyparsing_version,
    description="Python parsing module",
    long_description=pyparsing_main_doc,
    long_description_content_type="text/x-rst",
    author="Paul McGuire",
    author_email="ptmcg@users.sourceforge.net",
    url="https://github.com/pyparsing/pyparsing/",
    download_url="https://pypi.org/project/pyparsing/",
    license="MIT License",
    packages=packages,
    python_requires=">=3.5",
    extras_require={
        "diagrams": ["railroad-diagrams", "jinja2"],
    },
    package_data={"pyparsing.diagram": ["*.jinja2"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
