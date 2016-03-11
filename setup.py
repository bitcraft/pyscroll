#!/usr/bin/env python
#encoding: utf-8
#python setup.py sdist upload -r pypi
from setuptools import setup

setup(name='pyscroll',
      version='2.16.6',
      description='Scrolling maps library for pygame and python 2.7 & 3.3+',
      author='bitcraft',
      author_email='leif.theden@gmail.com',
      url='http://github.com/bitcraft/pyscroll',
      packages=['pyscroll'],
      install_requires=['pygame', 'six'],
      license='LGPLv3',
      long_description='see readme.md',
      package_data={
          'pyscroll': ['license.txt', 'readme.md']},
      classifiers=[
          "Intended Audience :: Developers",
          "Development Status :: 4 - Beta",
          "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Topic :: Games/Entertainment",
          "Topic :: Multimedia :: Graphics",
          "Topic :: Software Development :: Libraries :: pygame",
      ],
)
