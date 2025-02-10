#!@PYTHON@

'''
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}


Helper program for WnckWindowManager that retrieves window information
using Wnck and prints them to stdout in JSON format.

The information to print is specified by the program arguments.

This is a separate program to avoid a Wnck (and thus X11 and GTK 3)
dependency in the main application.
'''

import gi
gi.require_version('Wnck', '3.0')
from gi.repository import Wnck

import json
import os
import re
import sys

class WindowInfoProvider:

  def __init__(self):
    # require GDK_BACKEND=x11 environment variable to be set
    # as Wnck only works on X11/XWayland
    if os.environ.get('GDK_BACKEND') != 'x11':
      print('Error: Environment variable GDK_BACKEND=x11 not set', file=sys.stderr)
      exit(1)

    self.wnck_screen = Wnck.Screen.get_default()
    self.wnck_screen.force_update()

  def print_window_infos(self):
    '''
    Print JSON array containing information about all windows to stdout.
    '''
    active_workspace = self.wnck_screen.get_active_workspace()
    win_infos = []
    stacking_index = 0
    for window in self.wnck_screen.get_windows_stacked():
      # client geometry is used unless window has client side decorations,
      # in which case frame geometry is used;
      # assume that client side decoration is used when client rect contains the frame rect
      client_x, client_y, client_width, client_height = window.get_client_window_geometry()
      frame_x, frame_y, frame_width, frame_height = window.get_geometry()
      client_contains_frame = (client_x <= frame_x) and (client_y <= frame_y) \
          and (client_x + client_width >= frame_x + frame_width) \
          and (client_y + client_height >= frame_y + frame_height)
      if client_contains_frame:
        toplevel_x, toplevel_y, toplevel_width, toplevel_height = frame_x, frame_y, frame_width, frame_height
      else:
        toplevel_x, toplevel_y, toplevel_width, toplevel_height = client_x, client_y, client_width, client_height
      title = window.get_name()
      # strip additional trailing Left-to-Right Mark (U+200E), seen with KWin
      if title[-1] == '\u200e':
        title = title[0:-1]
      # KWin 5 (but not KWin 6) adds suffix to window title when there are multiple windows with the
      # same name, e.g. first window: "Hypertext", second window: "Hypertext <2>".
      # Remove the suffix as the accessible name retrieved from AT-SPI2 doesn't have it either
      regex = '^.* <[0-9]+>$'
      if re.match(regex, title):
        title = title[0:title.rfind(' ')]
      # workspace can be None if window is on all workspaces, so only consider case
      # of an actually returned workspace differing from the active one as not on active workspace
      workspace = window.get_workspace()
      on_active_workspace = (not workspace) or (not active_workspace) or window.is_on_workspace(active_workspace)
      pid = window.get_pid()

      win_infos.append(
          {
              'caption': title,
              'geometry.x': toplevel_x,
              'geometry.y': toplevel_y,
              'geometry.width': toplevel_width,
              'geometry.height': toplevel_height,
              'isOnCurrentWorkspace': on_active_workspace,
              'pid': pid,
              'stackingOrder': stacking_index
          }
      )
      stacking_index = stacking_index + 1

    print(json.dumps(win_infos))

  def print_icon_infos(self, window_names):
    '''
    Print relevant information about the window icon that can be
    used to create a GdkPixbuf.Pixbuf from it.
    The information will be printed for the first
    window whose name matches one in the given list.

    @param window_names: List of window names/titles.
    @type list[str]
    '''
    for win in self.wnck_screen.get_windows():
      wname = win.get_name()
      for name in window_names:
        if name == wname:
          pixbuf = win.get_mini_icon()
          result = {
            'pixels': pixbuf.get_pixels().hex(),
            'has_alpha': pixbuf.get_has_alpha(),
            'bits_per_sample': pixbuf.get_bits_per_sample(),
            'width': pixbuf.get_width(),
            'height': pixbuf.get_height(),
            'rowstride': pixbuf.get_rowstride()
          }
          print(json.dumps(result))
          return

    print(json.dumps({}))


if __name__ == '__main__':
  if len(sys.argv) < 2:
    print('Usage: `wnck-get-window-infos.py window-infos` or `wnck-get-window-infos.py icon win_name1 [win_name2 ...]`', file=sys.stderr)
    exit(1)

  provider = WindowInfoProvider()
  if sys.argv[1] == "window-infos":
    provider.print_window_infos()
  elif sys.argv[1] == "icon":
    provider.print_icon_infos(sys.argv[2:])
  else:
    print('Usage: `wnck-get-window-infos.py window-infos` or `wnck-get-window-infos.py icon win_name1 [win_name2 ...]`', file=sys.stderr)
