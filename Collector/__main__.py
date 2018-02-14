# encoding: utf-8
'''
Collector -- Crash processing client

Provide process and class level interfaces to process crash information with
a remote server.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import sys
from .Collector import main

sys.exit(main())
