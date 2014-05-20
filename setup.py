#!/usr/bin/env python
#encoding: utf-8

from setuptools import setup

setup(name='pyscroll',
      version='2.14.2',
      description='Scrolling library for pygame and python 2.7 & 3.3',
      author='bitcraft',
      author_email='leif.theden@gmail.com',
      url='http://github.com/bitcraft/pyscroll',
      packages=['pyscroll', 'tutorial'],
      install_requires=['six'],
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
          "Topic :: Games/Entertainment",
          "Topic :: Multimedia :: Graphics",
          "Topic :: Software Development :: Libraries :: pygame",
      ],
)
