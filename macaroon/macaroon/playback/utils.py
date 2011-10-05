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

from gi.repository import Gdk
import pyatspi

keymap = Gdk.Keymap.get_default()

def getKeyCodeFromVal(keyval):
  global keymap
  success, entry = keymap.get_entries_for_keyval(keyval)
  if not entry:
    raise TypeError("Invalid key name")
  else:
    return entry[0][0]

def getActiveFrame():
  desktop = pyatspi.Registry.getDesktop(0)
  active_frame = None
  for app in desktop:
    if app is None: continue
    for acc in app:
      if acc is None: continue
      if acc.getRole() == pyatspi.ROLE_FRAME:
        state_set = acc.getState()
        if state_set.contains(pyatspi.STATE_ACTIVE):
          active_frame = acc
        state_set.unref()
        if active_frame is not None:
          return active_frame
  return None
