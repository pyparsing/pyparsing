set MAKING_PYPARSING_RELEASE=1

copy ..\sourceforge\svn\trunk\src\CHANGES .
copy ..\sourceforge\svn\trunk\src\setup.py .
copy ..\sourceforge\svn\trunk\src\pyparsing.py .

rmdir build
rmdir dist

copy/y MANIFEST.in_src MANIFEST.in
if exist MANIFEST del MANIFEST
python setup.py sdist --formats=gztar,zip

copy/y MANIFEST.in_bdist MANIFEST.in
if exist MANIFEST del MANIFEST

python setup.py bdist_wininst --target-version=3.0 --plat-name=win32
python setup.py bdist_wininst --target-version=3.1 --plat-name=win32
python setup.py bdist_wininst --target-version=3.2 --plat-name=win32
python setup.py bdist_wininst --target-version=3.3 --plat-name=win32

set MAKING_PYPARSING_RELEASE=
