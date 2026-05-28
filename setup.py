"""
setup.py — legacy compatibility shim.

All real configuration lives in pyproject.toml.
This file exists only so that:
  · pip install -e .      works on older pip versions
  · python setup.py ...   continues to function

Do not add configuration here.
"""

from setuptools import setup

if __name__ == "__main__":
    setup()
