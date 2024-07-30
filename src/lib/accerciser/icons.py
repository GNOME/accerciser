'''
Defines a mapping from widget roles to icons representing them.

@author: Peter Parente
@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2006, 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import gi

from gi.repository import Gtk as gtk
from gi.repository import GdkPixbuf
from gi.repository import GObject

import sys, os, glob

from . import window_manager

from pyatspi.constants import *

ICONS_PATH = os.path.join(sys.prefix, 'share',
                          'accerciser', 'pixmaps', 'hicolor', '22x22')

if not os.path.exists(ICONS_PATH):
   ICONS_PATH = os.path.join(os.path.split(os.getcwd())[0], 'pixmaps')

def getIcon(acc):
  '''
  Loads an icon for the given application or accessible widget. Tries to use
  the current theme or the window manager to get application icons. Uses own
  icons for widgets.
  '''
  theme = gtk.IconTheme.get_default()
  try:
    role_name = acc.getRoleName()
    role = acc.getRole()
    if role_name == 'application':
      # try the theme first
      try:
        return theme.load_icon(acc.name, 24, gtk.IconLookupFlags.USE_BUILTIN)
      except GObject.GError:
        pass

      # then try the WindowManager
      win_manager = window_manager.get_window_manager()
      icon = win_manager.getApplicationIcon(acc)
      return icon
    else:
      name = role_name.replace(' ', '')
      try:
        fn = os.path.join(ICONS_PATH, '%s.png' % name)
        return GdkPixbuf.Pixbuf.new_from_file(fn)
      except GObject.GError:
        pass
  except Exception as e:
    pass
  fn = os.path.join(ICONS_PATH, 'filler.png')
  return GdkPixbuf.Pixbuf.new_from_file(fn)
