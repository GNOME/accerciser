# Macaroon - a desktop macro tool
# Copyright (C) 2007 Eitan Isaacson <eitan@ascender.com>
# All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "COPYING" in the source distribution for more information.

# Headers in this file shall remain intact.

from .__init__ import *

import sys

sys.stderr.write('WARNING: This module (%s) is deprecated, use %s\n' % \
                   (__name__, '.'.join((__name__).split('.')[:-1])))
