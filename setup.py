#!/usr/bin/env python
from setuptools import setup

if __name__ == '__main__':
    setup(name = "FuzzManager",
          version = "0.1",
          packages = ['Collector', 'FTB', 'FTB.Running', 'FTB.Signatures'],
          install_requires = ['numpy==1.11.2', 'requests>=2.5.0'])

