from setuptools import setup
from Cython.Build import cythonize
import os

# This will find all .py files in the pyparsing package
py_files = [os.path.join("pyparsing", file) for file in os.listdir("pyparsing") if file.endswith(".py")]
py_files.append(os.path.join("pyparsing", "diagram", "__init__.py"))
# Cythonize those files
extensions = cythonize(py_files)

setup(
    name="pyparsing",
    version="3.1.4",
    ext_modules=extensions,
)