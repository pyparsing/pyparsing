from setuptools import setup, Extension
from Cython.Build import cythonize
import os
from Cython.Distutils import build_ext as cython_build_ext
import multiprocessing
import subprocess
import sys

# Define the base directory
base_dir = "pyparsing"

# Find all .py files in the pyparsing package recursively
py_files = []
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".py"):
            py_files.append(os.path.join(root, file))

# Compiler directives
base_compiler_directives = {
    "language_level": 3,
    "overflowcheck": True,
    "cdivision": True,
    "infer_types": True,
    "embedsignature": True,
    "c_api_binop_methods": True,
    "profile": True,
}

# Extra compile and link arguments
extra_compile_args = [] # ["-O0", "-g"]  # Disable optimizations, include debug symbols
extra_link_args = []

# Create Extension objects
extensions = []
for py_file in py_files:
    module_name = py_file.replace(os.path.sep, ".")[:-3]  # Convert file path to module name
    extensions.append(
        Extension(
            module_name,
            [py_file],
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
        )
    )
    
extensions = cythonize(extensions, compiler_directives=base_compiler_directives, nthreads=8)
    
# Get the number of physical cores
num_cores = multiprocessing.cpu_count()

# Custom build_ext command to include -j option
class build_ext(cython_build_ext):
    def initialize_options(self):
        super().initialize_options()
        self.parallel = num_cores
    def run(self):
        # Run the original build_ext command
        super().run()

        # Now, strip the built shared objects
        for ext in self.extensions:
            fullname = self.get_ext_fullpath(ext.name)
            if os.path.exists(fullname):
                print(f"Stripping debug symbols from {fullname}")
                if sys.platform.startswith('linux'):
                    subprocess.call(['strip', fullname])
                elif sys.platform == 'darwin':
                    subprocess.call(['strip', '-x', fullname])

setup(
    name="pyparsing",
    version="3.2.0",
    ext_modules=extensions,
    cmdclass={'build_ext': build_ext},    
)
