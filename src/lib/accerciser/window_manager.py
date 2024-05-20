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
  preferred = os.getenv('ACCERCISER_WINDOW_MANAGER')
  if preferred == 'kwin':
    return KWinWindowManager()
  if preferred == 'gnomeshell':
    return GnomeShellWindowManager()
  return WindowManager()


class WindowGeometry:
  '''
  Class that represents the geometry (position and size) of a
  (system) window.
  '''

  def __init__(self, x, y, width, height):
    self.x = x
    self.y = y
    self.width = width
    self.height = height


class WindowInfo:
  '''
  Class that represents relevant information of a (system) window.
  '''

  def __init__(self, title, x, y, width, height, stacking_index=0,
               on_current_workspace=True, buffer_geometry=None):
    self.title = title
    self.x = x
    self.y = y
    self.width = width
    self.height = height
    self.stacking_index = stacking_index
    self.on_current_workspace = on_current_workspace
    self.buffer_geometry = buffer_geometry


class WindowManager:
  '''
  Class that provides information related to windows on the screen and the
  screen itself.
  This includes fetching information from the X11 window manager or
  Wayland compositor.
  Any handling specific to a particular window system should be done in this
  class.
  '''

  def getToolkitNameAndVersion(self, acc):
    '''
    Return the name and major version number of the toolkit
    used by the application that the given accessible belongs to.

    @param acc: Accessible for whose application to retrieve
                the toolkit info.
    @type acc: Atspi.Accessible
    @return: The toolkit name and major version, or `(None, None)`
             if that information couldn't be retrieved.
    @rtype: tuple(str, int)
    '''
    app = acc.get_application()
    if app and app.role == pyatspi.ROLE_APPLICATION:
      toolkit = app.get_toolkit_name()
      version = app.get_toolkit_version()
      if not version or (not isinstance(version, str)):
        return True
      try:
        major_version = int(version.split('.')[0])
        return toolkit, major_version
      except ValueError:
        pass
    return None, None


  def supportsScreenCoords(self, acc):
    '''
    Returns False when the accessible does not support
    querying screen coordinates directly via AT-SPI,
    otherwise True.
    '''
    app = acc.get_application()
    toolkit, major_version = self.getToolkitNameAndVersion(acc)
    if toolkit and major_version:
      # Gtk 4 doesn't support global/screen coords
      if toolkit.lower() == 'gtk' and (major_version >= 4):
          return False
    return True

  def getWindowInfos(self):
    '''
    Retrieve window information for all (system) windows.

    @return: Window information for all windows.
    @rtype: list[WindowInfo]
    '''
    wnck_screen = Wnck.Screen.get_default()
    active_workspace = wnck_screen.get_active_workspace()
    win_infos = []
    stacking_index = 0
    for window in wnck_screen.get_windows_stacked():
      toplevel_x, toplevel_y, toplevel_width, toplevel_height = window.get_client_window_geometry()
      title = window.get_name()
      # workspace can be None if window is on all workspaces, so only consider case
      # of an actually returned workspace differing from the active one as not on active workspace
      workspace = window.get_workspace()
      on_active_workspace = (not workspace) or (not active_workspace) or window.is_on_workspace(active_workspace)
      win_info = WindowInfo(title, toplevel_x, toplevel_y, toplevel_width, toplevel_height,
                            stacking_index=stacking_index, on_current_workspace=on_active_workspace)
      win_infos.append(win_info)
      stacking_index = stacking_index + 1

    return win_infos

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
    candidates = []
    win_infos = self.getWindowInfos()
    for window in win_infos:
      # for GTK 3 apps (at least seen with gedit and Evince), the window-local
      # coordinates for accessibles and size of the top-level frame refer to the
      # buffer geometry, so use that if available
      if window.buffer_geometry:
        toolkit, major_version = self.getToolkitNameAndVersion(toplevel)
        if toolkit and toolkit.lower() == 'gtk' and major_version == 3:
          window.x = window.buffer_geometry.x
          window.y = window.buffer_geometry.y
          window.width = window.buffer_geometry.width
          window.height = window.buffer_geometry.height

      # match by name, but also consider windows for which libwnck/the window manager (?)
      # has appended a suffix to distinguish multiple windows with the same name
      # (seen at least on KDE Plasma X11, e.g. first window: "Hypertext",
      # second window: "Hypertext <2>") - but in the a11y tree, both have the same name
      #
      # also accept an additional trailing Left-to-Right Mark (U+200E)
      # (also seen on KDE Plasma)
      regex = '^' + re.escape(toplevel.name) + '( <[0-9]*>)?(\u200e)?$'
      if re.match(regex, window.title):
        candidates.append(window)

    window = None
    if len(candidates) == 1:
      window = candidates[0]
    elif len(candidates) > 1:
      # in case of multiple candidates, prefer one where size reported by AT-SPI matches Wnck one
      atspi_width, atspi_height = toplevel.queryComponent().getSize()
      for candidate in candidates:
        if candidate.width == atspi_width and candidate.height == atspi_height:
          window = candidate
          break
      # if size doesn't match for any, use first candidate
      if window is None:
        window = candidates[0]

    return window

  def getCurrentWorkspaceWindowOrder(self):
    '''
    Get list of names of windows on the current workspace
    in stacking order.

    The list is in bottom-to-top order.
    '''
    windows = self.getWindowInfos()

    # filter out windows not on the current workspace
    windows = [win for win in windows if win.on_current_workspace]

    # sort according to stacking order
    def get_stacking_index(win):
      return win.stacking_index
    windows.sort(key=get_stacking_index)
    window_titles = [win.title for win in windows]
    return window_titles

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

  def getWindowInfos(self):
    # Retrieve information on all windows from KWin via the KWin scripting API
    #
    # See the JavaScript script used for details on the script output that gets
    # processed here
    if self.kwin_version >= 6:
      kwin_script_path = os.path.join(sys.prefix, 'share', 'accerciser', 'kwin-scripts', 'kwin6-retrieve-window-infos.js')
    else:
      kwin_script_path = os.path.join(sys.prefix, 'share', 'accerciser', 'kwin-scripts', 'kwin5-retrieve-window-infos.js')

    window_infos = []
    try:
      window_data = self._runKWinScript(kwin_script_path)
      for win in window_data:
        buffer_geometry = WindowGeometry(win["bufferGeometry.x"], win["bufferGeometry.y"],
                                         win["bufferGeometry.width"], win["bufferGeometry.height"])
        win_info = WindowInfo(win["caption"], win["geometry.x"], win["geometry.y"],
                              win["geometry.width"], win["geometry.height"],
                              stacking_index=win["stackingOrder"],
                              on_current_workspace=win["isOnCurrentWorkspace"],
                              buffer_geometry=buffer_geometry)
        window_infos.append(win_info)
    except Exception:
      pass

    return window_infos

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


class GnomeShellWindowManager(WindowManager):
  '''
  WindowManager implementation that retrieves information from
  Accerciser's GNOME Shell extension that queries the information
  from Mutter and provides them via a DBus service.
  '''

  def _getWindowData(self):
    '''
    Query window information from the Accerciser GNOME Shell extension
    via DBus.
    '''
    session_bus = dbus.SessionBus()
    accerciser_dbus_object = session_bus.get_object('org.gnome.accerciser.Accerciser', '/org/gnome/accerciser/Accerciser')
    accerciser_interface = dbus.Interface(accerciser_dbus_object, 'org.gnome.accerciser.Accerciser')
    data_json = accerciser_interface.GetWindowInfos()
    data = json.loads(data_json)
    return data

  def getWindowInfos(self):
    window_infos = []
    try:
      window_data = self._getWindowData()
      for win in window_data:
        win_info = WindowInfo(win["caption"], win["bufferGeometry.x"], win["bufferGeometry.y"],
                              win["bufferGeometry.width"], win["bufferGeometry.height"],
                              on_current_workspace=win["isOnCurrentWorkspace"])
        window_infos.append(win_info)
    except Exception:
      pass

    return window_infos

  def supportsScreenCoords(self, acc):
    # never query screen/desktop coordinates from AT-SPI, but always
    # use window position retrieved from Mutter/GNOME Shell extension
    return False

  def getMousePosition(self):
    try:
      session_bus = dbus.SessionBus()
      accerciser_dbus_object = session_bus.get_object('org.gnome.accerciser.Accerciser', '/org/gnome/accerciser/Accerciser')
      accerciser_interface = dbus.Interface(accerciser_dbus_object, 'org.gnome.accerciser.Accerciser')
      x, y = accerciser_interface.GetMousePosition()
      return x, y
    except Exception:
      return 0, 0
