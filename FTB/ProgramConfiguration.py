#!/usr/bin/env python
# encoding: utf-8
'''
ProgramConfiguration -- Configuration of a target program

Container class that stores various configuration parameters, like platform,
product, OS, version and other parameters relevant for reproducing the issue.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

class ProgramConfiguration():
    def __init__(self, product, platform, os, version=None, environment=None, args=None):
        '''
        @type product: string
        @param product: The name of the product/program/branch tested
        @type platform: string
        @param platform: Platform on which is tested (e.g. x86, x86-64 or arm)
        @type os: string
        @param os: Operating system on which is tested (e.g. linux, windows, macosx)
        '''
        self.product = product.lower()
        self.platform = platform.lower()
        self.os = os.lower()
        self.version = version
        
        if environment is None:
            environment = {}
        
        if args is None:
            args = []
        
        assert isinstance(environment, dict)
        assert isinstance(args, list)
        
        self.environment = environment
        self.args = args