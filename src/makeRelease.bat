set MAKING_PYPARSING_RELEASE=1

copy ..\sourceforge\svn\pyparsing_1.5.x\src\CHANGES .
copy ..\sourceforge\svn\pyparsing_1.5.x\src\setup.py .
copy ..\sourceforge\svn\pyparsing_1.5.x\src\pyparsing.py .

rmdir build
rmdir dist

copy/y MANIFEST.in_src MANIFEST.in
if exist MANIFEST del MANIFEST
python setup.py sdist --formats=gztar,zip

copy/y MANIFEST.in_bdist MANIFEST.in
if exist MANIFEST del MANIFEST

python setup.py bdist_wininst --target-version=2.4 --plat-name=win32
python setup.py bdist_wininst --target-version=2.5 --plat-name=win32
python setup.py bdist_wininst --target-version=2.6 --plat-name=win32
python setup.py bdist_wininst --target-version=2.7 --plat-name=win32

set MAKING_PYPARSING_RELEASE=
