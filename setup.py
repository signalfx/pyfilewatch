#!/usr/bin/env python

# Copyright (C) 2013 - 2014 SignalFuse, Inc.
# Setuptools install description file.

from setuptools import setup, find_packages

from filewatch import __title__ as name, __version__ as version

with open('README.md') as readme:
    long_description = readme.read()

setup(
    name=name,
    version=version,
    description='Watch files and directories in python. Also supports tailing and glob file patterns.',
    long_description=long_description,
    zip_safe=True,
    packages=find_packages(),
    install_requires=[
        'argparse>=1.2.1'
    ],
    classifiers=[],
    entry_points={
    },

    url='http://github.com/signalfx/pyfilewatch',
)
