xcopy /y .\sourceforge\svn\trunk\src\pyparsing.py .
python c:\python27\scripts\epydoc -v --name pyparsing -o htmldoc --inheritance listed --no-private pyparsing.py
