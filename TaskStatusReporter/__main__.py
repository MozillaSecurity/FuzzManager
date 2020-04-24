# encoding: utf-8
'''
TaskStatusReporter -- Simple Task status reporting tool for TaskManager

Provide process and class level interfaces to send simple textual
status reports to TaskManager.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    jschwartzentruber@mozilla.com
'''
import sys
from .TaskStatusReporter import main

sys.exit(main())
