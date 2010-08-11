set MAKING_PYPARSING_RELEASE=1

if exist pyparsing.py del pyparsing.py
rmdir build
rmdir dist

copy/y MANIFEST.in_src MANIFEST.in
if exist MANIFEST del MANIFEST
python setup.py sdist --formats=gztar,zip

copy/y MANIFEST.in_bdist MANIFEST.in
if exist MANIFEST del MANIFEST

copy/y pyparsing_py2.py pyparsing.py
python setup.py bdist_wininst --target-version=2.4
python setup.py bdist_wininst --target-version=2.5
python setup.py bdist_wininst --target-version=2.6
python setup.py bdist_wininst --target-version=2.7

copy/y pyparsing_py3.py pyparsing.py
python setup.py bdist_wininst --target-version=3.0
python setup.py bdist_wininst --target-version=3.1
python setup.py bdist_wininst --target-version=3.2

set MAKING_PYPARSING_RELEASE=