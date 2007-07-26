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

import pyatspi
import gtk
from playback_sequence import *

# Minimum time before a key press
press_min = 300
# Maximum time before a key release
release_max = 400

class KeyPressAction(AtomicAction):
  def __init__(self, delta_time, key_code):
    if delta_time < press_min: delta_time = press_min
    AtomicAction.__init__(self, delta_time, self._keyPress, key_code)
  def _keyPress(self, key_code):
    pyatspi.Registry.generateKeyboardEvent(key_code, None, pyatspi.KEY_PRESS)

class KeyReleaseAction(AtomicAction):
  def __init__(self, delta_time, key_code):
    if delta_time > release_max: delta_time = release_max
    AtomicAction.__init__(self, delta_time, self._keyRelease, key_code)
  def _keyRelease(self, key_code):
    pyatspi.Registry.generateKeyboardEvent(key_code, None, pyatspi.KEY_RELEASE)

class WaitForWindowActivate(WaitAction):
  def __init__(self, frame_re, application_re, timeout=5000):
    WaitAction.__init__(self, timeout)
    self._frame_re = frame_re
    self._application_re = application_re
  def listenFor(self):
    pyatspi.Registry.registerEventListener(self._onWindowActivate, 
                                           'window:activate')
  def _onWindowActivate(self, event):
    if event.source.name == self._frame_re:
      self.endWait()

class WaitForFocus(WaitAction):
  def __init__(self, acc_path, acc_role, timeout=5000):
    WaitAction.__init__(self, timeout)
    self._acc_path = acc_path
    self._acc_role = acc_role
  def listenFor(self):
    pyatspi.Registry.registerEventListener(self._onFocus, 
                                           'focus')
  def _onFocus(self, event):
    if (self._acc_path is None or 
        self._acc_path == pyatspi.getPath(event.source)) and \
        (self._acc_role is None or self._acc_role == event.source.getRole()):
      self.endWait()
