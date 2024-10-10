from setuptools import setup
from Cython.Build import cythonize
import os

# This will find all .py files in the pyparsing package
py_files = [os.path.join("pyparsing", file) for file in os.listdir("pyparsing") if file.endswith(".py")]

# Cythonize those files
extensions = cythonize(py_files)

setup(
    name='cythonized_pyparsing',
    ext_modules=extensions,
)