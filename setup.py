#!/usr/bin/env python

"""Setup script for the pyparsing module distribution."""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from io import open

# The directory containing this file
README_name = __file__.replace("setup.py", "README.rst")

# The text of the README file
with open(README_name, encoding='utf8') as README:
    pyparsing_main_doc = README.read()

modules = [
    "pyparsing.pyparsing",
]

pyparsing_version = "3.0.0.1"

setup(  # Distribution meta-data
    name="pyparsing",
    version=pyparsing_version,
    description="Python parsing module",
    long_description=pyparsing_main_doc,
    author="Paul McGuire",
    author_email="ptmcg@users.sourceforge.net",
    url="https://github.com/pyparsing/pyparsing/",
    download_url="https://pypi.org/project/pyparsing/",
    license="MIT License",
    py_modules=modules,
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
