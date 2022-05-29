## Development
     
After forking the pyparsing repo, and cloning your fork locally, install the libraries needed to run tests

     pip install -r tests/requirements.txt
     pre-commit install
         
Run the tests to ensure your environment is setup 
     
     python -m unittest discover tests

### mypy ignore tests

`tests/mypy-ignore-cases/` is populated with python files which are meant to be
checked using `mypy --warn-unused-ignores`.

To check these files, run

    tox -e mypy-tests
