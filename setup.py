#!/usr/bin/env python
from setuptools import setup

if __name__ == '__main__':
    with open('requirements-client.txt') as requirements_fp:
        requirements = requirements_fp.read().strip().splitlines()
    setup(name = "FuzzManager",
          version = "0.1",
          packages = ['Collector', 'FTB', 'FTB.Running', 'FTB.Signatures'],
          install_requires = requirements)
