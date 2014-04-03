#!/usr/bin/env python
#encoding: utf-8

import os
from setuptools import setup
import pyscroll


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(name="pyscroll",
      version=pyscroll.__version__,
      description=pyscroll.__description__,
      author=pyscroll.__author__,
      author_email=pyscroll.__author_email__,
      packages=['pyscroll', 'tests'],
      install_requires=['pygame'],
      license="LGPLv3",
      long_description=read('README.md'),
      package_data={
          'pyscroll': ['LICENSE', 'README.md']},
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
