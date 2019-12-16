#!/usr/bin/env python
from setuptools import setup

if __name__ == '__main__':
    setup(
        use_scm_version=True,
        setup_requires=['setuptools>=30.3', 'setuptools_scm'],
    )
