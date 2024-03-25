'''
Defines classes to manage information for windows and the screen.

@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

from gi.repository import Gdk
from gi.repository import Wnck
import pyatspi

import datetime
import dbus
import json
import os
import re
import subprocess
import sys


def get_window_manager():
  if os.getenv('ACCERCISER_WINDOW_MANAGER') == 'kwin':
    return KWinWindowManager()
  return WindowManager()


class WindowInfo:
  '''
  Class that represents relevant information of a (system) window.
  '''

  def __init__(self, title, x, y, width, height):
    self.title = title
    self.x = x
    self.y = y
    self.width = width
    self.height = height


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

  def getWindowOrder(self):
    '''
    Get list of names of windows in stacking order.

    The list is in bottom-to-top order.
    '''
    wnck_screen = Wnck.Screen.get_default()
    window_order = [w.get_name() for w in wnck_screen.get_windows_stacked()]
    return window_order

  def getWindowInfo(self, toplevel):
      '''
      Get information on the (system) window that the toplevel
      corresponds to, if possible.

      @param toplevel: The top level for which to receive the corresponding
                       window info.
      @type toplevel: Atspi.Accessible
      @return: The WindowInfo for the toplevel's system window, or None.
      @rtype: WindowInfo
      '''
      window = self.getWnckWindow(toplevel)
      if not window:
        return None

      toplevel_x, toplevel_y, toplevel_width, toplevel_height = window.get_client_window_geometry()
      return WindowInfo(window.get_name(), toplevel_x, toplevel_y, toplevel_width, toplevel_height)

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
      # try to get position info for the corresponding system window
      # and calculate screen coordinates from screen coords of the system
      # window and window-relative coords of the object
      win_info = self.getWindowInfo(toplevel)
      if win_info:
        extents = component_iface.getExtents(pyatspi.WINDOW_COORDS)
        extents.x += win_info.x
        extents.y += win_info.y
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

  def getMousePosition(self):
    '''
    Get current mouse/pointer position in desktop/global coordinates.

    @return: The (x, y) coordinates of the mouse/pointer position.
    @rtype: tuple(int, int)
    '''
    display = Gdk.Display.get_default()
    seat = display.get_default_seat()
    pointer = seat.get_pointer()
    screen, x, y =  pointer.get_position()
    return x, y


class KWinWindowManager(WindowManager):
  '''
  WindowManager implementation that retrireves information from KWin
  via its scripting API.

  KWin API documentation: https://develop.kde.org/docs/plasma/kwin/api/
  '''

  def __init__(self):
    # assume that KWin has the same major version as KDE Plasma
    plasma_version_str = os.getenv('KDE_SESSION_VERSION')
    if plasma_version_str:
      self.kwin_version = int(plasma_version_str)
    else:
      # fall back to 5 for now, might be relevant when KWin is used in non-Plasma environment
      self.kwin_version = 5

  def _runKWinScript(self, kwin_script_path):
    '''
    Run KWin script at the given path that returns output in JSON format
    and return the script output converted to a Python datastructure.
    '''
    # load the script, the method returns the script number/ID
    session_bus = dbus.SessionBus()
    scripting_dbus_object = session_bus.get_object('org.kde.KWin', '/Scripting')
    scripting_interface = dbus.Interface(scripting_dbus_object, 'org.kde.kwin.Scripting')
    script_id = scripting_interface.loadScript(kwin_script_path)

    # remember time before running the script, for retrieving relevant journal content below
    start_time = datetime.datetime.now()

    # run the script
    # DBus object path for script has changed between KWin 5 and 6
    if self.kwin_version >= 6:
      script_object_path = '/Scripting/Script' + str(script_id)
    else:
      script_object_path = '/' + str(script_id)
    script_dbus_object = session_bus.get_object('org.kde.KWin', script_object_path)
    script_interface = dbus.Interface(script_dbus_object, 'org.kde.kwin.Script')
    script_interface.run()

    # currently, no DBus signals are created when the script prints the relevant information,
    # see https://bugs.kde.org/show_bug.cgi?id=477069
    # and https://bugs.kde.org/show_bug.cgi?id=392840
    # and https://bugs.kde.org/show_bug.cgi?id=445058
    # As a workaround, retrieve the script output from the journal instead,
    # s.a. discussion in https://bugs.kde.org/show_bug.cgi?id=445058
    comm = 'kwin_' + os.getenv('XDG_SESSION_TYPE')
    journalctl_output = subprocess.run('journalctl _COMM=' + comm + ' --output=cat --since "' + str(start_time) + '"',
                                       capture_output=True, shell=True).stdout.decode().rstrip().split("\n")
    lines = [line.lstrip("js: ") for line in journalctl_output]
    data_json = '\n'.join(lines)
    data = json.loads(data_json)

    # unload/unregister script again
    script_interface.stop()

    return data


  def _getKWinWindowData(self):
    '''
    Retrieve information on all windows from KWin via the KWin scripting
    API and return it as a list containing a dict entry for each window.

    See the JavaScript script used for details on returned information.
    '''
    if self.kwin_version >= 6:
      kwin_script_path = os.path.join(sys.prefix, 'share', 'accerciser', 'kwin-scripts', 'kwin6-retrieve-window-infos.js')
    else:
      kwin_script_path = os.path.join(sys.prefix, 'share', 'accerciser', 'kwin-scripts', 'kwin5-retrieve-window-infos.js')

    return self._runKWinScript(kwin_script_path)


  def getWindowInfo(self, toplevel):
    try:
      window_infos = self._getKWinWindowData()
      for win_data in window_infos:
        window_title = win_data["caption"]
        if window_title == toplevel.name:
          return WindowInfo(window_title, win_data["bufferGeometry.x"], win_data["bufferGeometry.y"],
                            win_data["bufferGeometry.width"], win_data["bufferGeometry.height"])
    except Exception:
      pass

    return None


  def getWindowOrder(self):
    try:
      window_infos = self._getKWinWindowData()
      windows = [(info["caption"], info["stackingOrder"]) for info in window_infos]

      # sort according to stacking order
      def get_stacking_order(win):
        return win[1]

      windows.sort(key=get_stacking_order)
      window_names = [win[0] for win in windows]
      return window_names
    except Exception as e:
      return []


  def supportsScreenCoords(self, acc):
    # never query screen/desktop coordinates from AT-SPI, but always
    # use KWin's window position
    return False


  def getMousePosition(self):
    try:
      kwin_script_path = os.path.join(sys.prefix, 'share', 'accerciser', 'kwin-scripts', 'kwin-retrieve-mouse-pointer-pos.js')
      data = self._runKWinScript(kwin_script_path)
      return data["mouse-pointer-pos.x"], data["mouse-pointer-pos.y"]
    except:
      return 0, 0
