import argparse

import pyparsing.version as ppv

parser = argparse.ArgumentParser(prog="python -m pyparsing")
parser.add_argument(
    "--version", "-V", action="store_true", help="show pyparsing version"
)

args = parser.parse_args()
if args.version:
    print(ppv.__version__)
