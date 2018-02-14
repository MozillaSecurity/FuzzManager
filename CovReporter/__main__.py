# encoding: utf-8
'''
CovReporter -- Coverage reporting client for CoverageManager

Provide process and class level interfaces to post-process and submit
coverage data to CoverageManager.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import sys
from .CovReporter import main

sys.exit(main())
