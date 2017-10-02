#!/usr/bin/env python
from setuptools import setup

if __name__ == '__main__':
    setup(name='FuzzManager',
          version='0.1.1',
          packages=['Collector', 'CovReporter', 'EC2Reporter', 'FTB', 'FTB.Running', 'FTB.Signatures', 'Reporter'],
          install_requires=['fasteners>=0.14.1', 'numpy>=1.11.2', 'requests>=2.5.0'])
