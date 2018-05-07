#!/usr/bin/env python
from setuptools import setup

if __name__ == '__main__':
    setup(classifiers=["Intended Audience :: Developers",
                       "Topic :: Software Development :: Testing",
                       "Topic :: Security",
                       "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
                       "Programming Language :: Python :: 2",
                       "Programming Language :: Python :: 2.7",
                       ],
          description="A fuzzing management tools collection",
          install_requires=['fasteners>=0.14.1', 'numpy>=1.11.2', 'requests>=2.5.0', 'six==1.11.0'],
          keywords="fuzz fuzzing security test testing",
          license="MPL 2.0",
          maintainer="Mozilla Fuzzing Team",
          maintainer_email="fuzzing@mozilla.com",
          name='FuzzManager',
          packages=['Collector', 'CovReporter', 'EC2Reporter', 'FTB', 'FTB.Running', 'FTB.Signatures', 'Reporter'],
          url="https://github.com/MozillaSecurity/FuzzManager",
          version='0.2.0')
