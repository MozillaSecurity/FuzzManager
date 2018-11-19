#!/usr/bin/env python
from setuptools import setup

if __name__ == '__main__':
    setup(author='Christian Holler',
          classifiers=['Intended Audience :: Developers',
                       'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
                       'Operating System :: OS Independent',
                       'Programming Language :: Python',
                       'Programming Language :: Python :: 2',
                       'Programming Language :: Python :: 2.7',
                       'Programming Language :: Python :: 3',
                       'Programming Language :: Python :: 3.4',
                       'Programming Language :: Python :: 3.5',
                       'Programming Language :: Python :: 3.6',
                       'Topic :: Software Development :: Testing',
                       'Topic :: Security'],
          description='A fuzzing management tools collection',
          install_requires=['fasteners>=0.14.1', 'numpy>=1.11.2', 'requests>=2.5.0', 'six==1.11.0'],
          keywords='fuzz fuzzing security test testing',
          license='MPL 2.0',
          maintainer='Mozilla Fuzzing Team',
          maintainer_email='fuzzing@mozilla.com',
          name='FuzzManager',
          packages=['Collector', 'CovReporter', 'EC2Reporter', 'FTB', 'FTB.Running', 'FTB.Signatures', 'Reporter'],
          url='https://github.com/MozillaSecurity/FuzzManager',
          version='0.3.1')
