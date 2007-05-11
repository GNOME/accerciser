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

import sys, os, glob
import gtk
import gobject
import wnck
from pyatspi.constants import *

ICONS_PATH = os.path.join(sys.prefix, 'share', 
                          'accerciser', 'pixmaps', 'hicolor', '22x22')

if not os.path.exists(ICONS_PATH):
   ICONS_PATH = os.path.join(os.path.split(os.getcwd())[0], 'pixmaps')

def getIcon(acc):
  '''
  Loads an icon for the given application or accessible widget. Tries to use
  the current theme or wnck to get application icons. Uses icons from 
  at-poke for widgets.
  '''
  theme = gtk.icon_theme_get_default()
  try:
    role_name = acc.getRoleName()
    role = acc.getRole()
    if role_name == 'application':
      # try the theme first
      try:
        return theme.load_icon(acc.name, 24, gtk.ICON_LOOKUP_USE_BUILTIN)
      except gobject.GError:
        pass
      # then try wnck
      s = wnck.screen_get_default()
      s.force_update()
      for win in s.get_windows():
        wname = win.get_name()
        for child in acc:
          if child.name == wname:
            return win.get_mini_icon()
      return None
    else:
      name = role_name.replace(' ', '')
      try:
        fn = os.path.join(ICONS_PATH, '%s.png' % name)
        return gtk.gdk.pixbuf_new_from_file(fn)
      except gobject.GError:
        pass
  except Exception, e:
    pass
  fn = os.path.join(ICONS_PATH, 'filler.png')
  return gtk.gdk.pixbuf_new_from_file(fn)
