#!/usr/bin/env python
#encoding: utf-8

import os
from setuptools import setup
import pyscroll


def read(file_name):
    with open(os.path.join(os.path.dirname(__file__), file_name)) as fd:
        return fd.read()


setup(name="pyscroll",
      version=pyscroll.__version__,
      description=pyscroll.__description__,
      author=pyscroll.__author__,
      author_email=pyscroll.__author_email__,
      packages=['pyscroll'],
      install_requires=['pygame'],
      license="LGPLv3",
      long_description='see https://github.com/bitcraft/pyscroll',
      classifiers=[
          "Intended Audience :: Developers",
          "Development Status :: 4 - Beta",
          "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
          "Programming Language :: Python :: 2.7",
          "Topic :: Games/Entertainment",
          "Topic :: Multimedia :: Graphics",
          "Topic :: Software Development :: Libraries :: pygame",
      ],
)
