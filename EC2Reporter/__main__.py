# encoding: utf-8
'''
EC2Reporter -- Simple EC2 status reporting tool for EC2SpotManager

Provide process and class level interfaces to send simple textual
status reports to EC2SpotManager.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import sys
from .EC2Reporter import main

sys.exit(main())
