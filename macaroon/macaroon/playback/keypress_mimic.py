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
_ = lambda x: x

# Highest granularity, define timing for every single press and release

# Minimum time before a key press
press_min = 300
# Maximum time before a key release
release_max = 400

class KeyPressAction(AtomicAction):
  def __init__(self, delta_time, key_code, key_name=None):
    if delta_time < press_min: delta_time = press_min
    self._key_name = key_name
    AtomicAction.__init__(self, delta_time, self._keyPress, key_code)
  def _keyPress(self, key_code):
    pyatspi.Registry.generateKeyboardEvent(key_code, None, pyatspi.KEY_PRESS)
    self.stepDone()
  def __str__(self):
    return _('Key press %s') % self._key_name or 'a key'

class KeyReleaseAction(AtomicAction):
  def __init__(self, delta_time, key_code, key_name=None):
    if delta_time > release_max: delta_time = release_max
    self._key_name = key_name
    AtomicAction.__init__(self, delta_time, self._keyRelease, key_code)
  def _keyRelease(self, key_code):
    pyatspi.Registry.generateKeyboardEvent(key_code, None, pyatspi.KEY_RELEASE)
    self.stepDone()
  def __str__(self):
    return _('Key release %s') % self._key_name or 'a key'


# A bit smarter about common interactions.

keystroke_interval = 200
mod_key_code_mappings = {
  'GDK_CONTROL_MASK' : 37,
  'GDK_MOD1_MASK' : 64,
  'GDK_LOCK_MASK' : 66,
  'GDK_SHIFT_MASK' : 50
  }

class KeyComboAction(AtomicAction):
  def __init__(self, key_combo, delta_time=0):    
    keyval, modifiers = gtk.accelerator_parse(key_combo)
    self._key_combo = key_combo
    AtomicAction.__init__(self, delta_time, self._doCombo, keyval, modifiers)
  def _doCombo(self, keyval, modifiers):
    interval = 0
    mod_hw_codes = map(mod_key_code_mappings.get, modifiers.value_names)
    for mod_hw_code in mod_hw_codes:
      gobject.timeout_add(interval, self._keyPress, mod_hw_code)
      interval += keystroke_interval
    gobject.timeout_add(interval, self._keyPressRelease, keyval)
    interval += keystroke_interval
    mod_hw_codes.reverse()
    for mod_hw_code in mod_hw_codes:
      gobject.timeout_add(interval, self._keyRelease, mod_hw_code)
      interval += keystroke_interval
    gobject.timeout_add(interval, self.stepDone)
  def _keyPress(self, hw_code):
    pyatspi.Registry.generateKeyboardEvent(hw_code, None, pyatspi.KEY_PRESS)
    return False
  def _keyRelease(self, hw_code):
    pyatspi.Registry.generateKeyboardEvent(hw_code, None, pyatspi.KEY_RELEASE)
    return False
  def _keyPressRelease(self, keyval):
    pyatspi.Registry.generateKeyboardEvent(keyval, None, pyatspi.KEY_SYM)
    return False
  def __str__(self):
    return _('Press %s') % self._key_combo

class TypeAction(AtomicAction):
  def __init__(self, string_to_type, delta_time=0, interval=None):    
    self._string_to_type = string_to_type
    if interval:
      self.interval = interval
    else:
      self.interval = keystroke_interval
    AtomicAction.__init__(self, delta_time, self._doType, string_to_type)
  def _doType(self, string_to_type):
    interval = 0
    for char in string_to_type:
      keyval = gtk.gdk.unicode_to_keyval(ord(char))
      gobject.timeout_add(interval, self._charType, keyval)
      interval += self.interval 
    gobject.timeout_add(interval, self.stepDone)
  def _charType(self, keyval):
    pyatspi.Registry.generateKeyboardEvent(keyval, None, pyatspi.KEY_SYM)
    return False
  def __str__(self):
    return _('Type %s') % self._string_to_type

# Things we might want to wait for.

class WaitForWindowActivate(WaitAction):
  def __init__(self, frame_re, application_re, timeout=30000):
    WaitAction.__init__(self, timeout)
    self._frame_re = frame_re
    self._application_re = application_re
    self.wait_for = ['window:activate']
  def onEvent(self, event):
    if event.source.name == self._frame_re:
      self.stepDone()
  def __str__(self):
    return _('Wait for window %s to be focused') % self._frame_re

class WaitForFocus(WaitAction):
  def __init__(self, acc_path, acc_role, timeout=5000):
    WaitAction.__init__(self, timeout)
    self._acc_path = acc_path
    self._acc_role = acc_role
    self.wait_for = ['focus']
  def onEvent(self, event):
    if (self._acc_path is None or 
        self._acc_path == pyatspi.getPath(event.source)) and \
        (self._acc_role is None or self._acc_role == event.source.getRole()):
      self.stepDone()
  def __str__(self):
    return _('Wait for %s to be focused') % self._acc_role
