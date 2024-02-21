'''
Defines classes to manage information for windows and the screen.

@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

from gi.repository import Wnck
import pyatspi
import re


class WindowManager:
  '''
  Class that provides information related to windows on the screen and the
  screen itself.
  This includes fetching information from the X11 window manager or
  Wayland compositor.
  Any handling specific to a particular window system should be done in this
  class.
  '''

  def supportsScreenCoords(self, acc):
    '''
    Returns False when the accessible does not support
    querying screen coordinates directly via AT-SPI,
    otherwise True.
    '''
    app = acc.get_application()
    if app and app.role == pyatspi.ROLE_APPLICATION:
      toolkit = app.get_toolkit_name()
      version = app.get_toolkit_version()
      if not version or (not isinstance(version, str)):
        return True
      try:
        major_version = int(version.split('.')[0])
        # Gtk 4 doesn't support global/screen coords
        if isinstance(toolkit, str) and (toolkit.lower() == 'gtk') and (major_version >= 4):
          return False
      except ValueError:
        pass
    return True

  def getWnckWindow(self, toplevel):
    '''
    Retrieve the Wnck window for the given toplevel accessible object.

    @param toplevel: The top level for which to receive the corresponding Wnck
                     window.
    @type toplevel: Atspi.Accessible
    @return: The Wnck window for the toplevel, or None.
    @rtype: Wnck.Window
    '''
    wnck_screen = Wnck.Screen.get_default()
    candidates = []
    for window in wnck_screen.get_windows():
      # match by name, but also consider windows for which libwnck/the window manager (?)
      # has appended a suffix to distinguish multiple windows with the same name
      # (seen at least on KDE Plasma X11, e.g. first window: "Hypertext",
      # second window: "Hypertext <2>") - but in the a11y tree, both have the same name
      #
      # also accept an additional trailing Left-to-Right Mark (U+200E)
      # (also seen on KDE Plasma)
      regex = '^' + toplevel.name + '( <[0-9]*>)?(\u200e)?$'
      if re.match(regex, window.get_name()):
        candidates.append(window)

    window = None
    if len(candidates) == 1:
      window = candidates[0]
    elif len(candidates) > 1:
      # in case of multiple candidates, prefer one where size reported by AT-SPI matches Wnck one
      atspi_width, atspi_height = toplevel.queryComponent().getSize()
      for candidate in candidates:
        candidate_x, candidate_y, candidate_width, candidate_height = candidate.get_client_window_geometry()
        if candidate_width == atspi_width and candidate_height == atspi_height:
          window = candidate
          break
      # if size doesn't match for any, use first candidate
      if window is None:
        window = candidates[0]

    return window

  def getScreenExtents(self, acc):
    '''
    Returns the extents of the given accessible object
    in screen/global coordinates.
    '''
    try:
      component_iface = acc.queryComponent()
    except NotImplementedError:
      return None

    screen_coords_supported = self.supportsScreenCoords(acc)

    if not screen_coords_supported:
      toplevel = acc
      while toplevel.parent and toplevel.parent.role != pyatspi.ROLE_APPLICATION:
        toplevel = toplevel.parent
      # try to find matching Wnck window and calculate screen coordinates from
      # screen coords of the Wnck window and window-relative coords of the object
      window = self.getWnckWindow(toplevel)
      if window:
        toplevel_x, toplevel_y, toplevel_width, toplevel_height = window.get_client_window_geometry()
        extents = component_iface.getExtents(pyatspi.WINDOW_COORDS)
        extents.x += toplevel_x
        extents.y += toplevel_y
        return extents

    # query screen coords directly via AT-SPI
    extents = component_iface.getExtents(pyatspi.DESKTOP_COORDS)
    return extents

  def convertScreenToWindowCoords(self, x, y, acc):
    '''
    Convert the given screen coordinates to coordinates relative to
    the window that the given accessible is in.

    @param x: x screen coordinate to convert to window coordinate.
    @type  x: int
    @param y: y screen coordinate to convert to window coordinate.
    @type  y: int
    @param acc: accessible in the window relative to which the coordinates
                should be calculated.
    @type acc:  Atspi.Accessible
    @return: The (x, y) coordinates relative to the window that the accessible is in.
    @rtype: tuple(int, int)
    '''
    try:
      component_iface = acc.queryComponent()
    except NotImplementedError:
      return x, y

    acc_screen_extents = self.getScreenExtents(acc)
    acc_window_extents = component_iface.getExtents(pyatspi.WINDOW_COORDS)

    win_x = acc_window_extents.x - acc_screen_extents.x + x
    win_y = acc_window_extents.y - acc_screen_extents.y + y
    return (win_x, win_y)
