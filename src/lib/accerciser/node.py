'''
Defines convenience classes representing tree nodes and bag objects.

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
from gi.repository import Gdk as gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Wnck as wnck
from gi.repository.Gio import Settings as GSettings
gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg as rsvg
import cairo
import pyatspi
import re
import string
from .tools import ToolsAccessor, parseColorString

gsettings = GSettings.new('org.a11y.Accerciser')
BORDER_COLOR, BORDER_ALPHA = parseColorString(
  gsettings.get_string('highlight-border'))

FILL_COLOR, FILL_ALPHA  = parseColorString(
  gsettings.get_string('highlight-fill'))

HL_DURATION = int(gsettings.get_double('highlight-duration')*1000)

class Bag(object):
  '''
  Bag class for converting a dicionary to an object with attributes.
  '''
  def __init__(self, **kwargs):
    self.__dict__.update(kwargs)

  def __str__(self):
    return ', '.join(list(vars(self).keys()))

class Node(GObject.GObject, ToolsAccessor):
  '''
  Node class that contains convient references to accessibility information
  for the currently selected node. A L{Node} instance will emit an
  'accessible-changed' signal when L{update} is called with a new accessible.

  @ivar desktop: The desktop accessible. It holds references to all the
  application L{Accessibility.Accessible}s
  @type desktop: L{Accessibility.Accessible}
  @ivar acc: The currently selected accessible.
  @type acc: L{Accessibility.Accessible}
  '''
  __gsignals__ = {'accessible-changed' :
                  (GObject.SignalFlags.RUN_FIRST,
                   None,
                   (GObject.TYPE_PYOBJECT,))}
  def __init__(self):
    self.desktop = pyatspi.Registry.getDesktop(0)
    self.acc = None
    self.tree_path = None
    GObject.GObject.__init__(self)

  def update(self, acc):
    '''
    Updates the information in this node for the given accessible including
    a reference to the accessible. Also emit the
    'accessible-changed' signal.

    @param acc: An accessible.
    @type acc: L{Accessibility.Accessible}
    '''
    if not acc or self.isMyApp(acc):
      return
    self.acc = acc
    self.tree_path = None
    if acc != self.desktop:
        # Don't highlight the entire desktop, it gets annoying.
        self.highlight()
    self.emit('accessible-changed', acc)

  def updateToPath(self, app_name, path):
    '''
    Update the node with a new accessible by providing a tree path
    in an application.

    @param app_name: Application name.
    @type app_name: string
    @param path: The accessible path in the application.
    @type path: list of integer
    '''
    acc = pyatspi.findDescendant(
      self.desktop,
      lambda x: x.name.lower()==app_name.lower(),
      breadth_first=True)
    if acc is None: return
    while path:
      child_index = path.pop(0)
      try:
        acc = acc[child_index]
      except IndexError:
        return
    self.update(acc)

  def supportsScreenCoords(self, app):
    '''
    Returns False when the app does not support
    querying screen coordinates directly via AT-SPI,
    otherwise True.
    '''
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
    wnck_screen = wnck.Screen.get_default()
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

    toplevel = acc
    while toplevel.parent and toplevel.parent.role != pyatspi.ROLE_APPLICATION:
      toplevel = toplevel.parent

    screen_coords_supported = True
    if toplevel.parent and toplevel.parent.role == pyatspi.ROLE_APPLICATION:
      screen_coords_supported = self.supportsScreenCoords(toplevel.parent)

    if not screen_coords_supported:
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

  def highlight(self):
    extents = self.getScreenExtents(self.acc)
    if extents is None or \
          0 in (extents.width, extents.height) or \
          -0x80000000 in (extents.x, extents.y):
      return
    ah = _HighLight(extents.x, extents.y,
                    extents.width, extents.height,
                    FILL_COLOR, FILL_ALPHA, BORDER_COLOR, BORDER_ALPHA,
                    2.0, 0)
    ah.highlight(HL_DURATION)

class _HighLight(gtk.Window):
  '''
  Highlight box class. Uses compositing when available. When not, it does
  transparency client-side.
  '''
  _svg = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg">
  <rect
       style="fill:$fill;fill-opacity:$fill_opacity;fill-rule:evenodd;stroke:$stroke;stroke-width:2;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-dasharray:none;stroke-opacity:$stroke_opacity"
       id="highlight"
       width="$width"
       height="$height"
       x="$x"
       y="$y"
       rx="2"
       ry="2" />
</svg>
"""
  def __init__(self, x, y, w, h,
               fill_color, fill_alpha,
               stroke_color, stroke_alpha,
               stroke_width, padding=0):

    # Initialize window.
    gtk.Window.__init__(self, type=gtk.WindowType.POPUP)

    # Normalize position for stroke and padding.
    self.x, self.y = x - padding, y - padding
    self.w, self.h = w + padding*2, h + padding*2

    # Determine if we are compositing.
    self._composited = self.is_composited()
    if self._composited:
      # Prepare window for transparency.
      screen = self.get_screen()
      visual = screen.get_rgba_visual()
      self.set_visual(visual)

    # Place window, and resize it, and set proper properties.
    self.set_app_paintable(True)
    self.set_decorated(False)
    self.set_keep_above(True)
    self.move(self.x, self.y)
    self.resize(self.w, self.h)
    self.set_accept_focus(False)
    self.set_sensitive(False)

    # Create SVG with given parameters.
    offset = stroke_width/2.0
    self.svg = string.Template(self._svg).substitute(
      x=offset, y=offset,
      width=int(self.w - stroke_width), height=int(self.h - stroke_width),
      fill=fill_color,
      stroke_width=stroke_width,
      stroke=stroke_color,
      fill_opacity=fill_alpha,
      stroke_opacity=stroke_alpha)

    # Connect "draw"
    self.connect("draw", self._onExpose)

  def highlight(self, duration=500):
    if duration > 0:
      GLib.timeout_add(duration, lambda w: w.destroy(), self)
      self.show_all()
    else:
      self.destroy()

  def _onExpose(self, widget, event):
    svgh = rsvg.Handle()
    try:
      svgh.write(bytes(self.svg, "utf-8"))
    except (GObject.GError, KeyError, ValueError) as ex:
      print ('Error reading SVG for display: %s\r\n%s', ex, self.svg)
      svgh.close()
      return
    svgh.close()

    if not self._composited:
      cairo_operator = cairo.OPERATOR_OVER
    else:
      cairo_operator = cairo.OPERATOR_SOURCE
    window = self.get_window()
    cr = window.cairo_create()
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
    cr.set_operator(cairo_operator)
    cr.paint()

    svgh.render_cairo(cr)
    del svgh

if __name__ == "__main__":
    hl = _HighLight(200, 200, 200, 200, '#ff0000',
                    0.5, '#ff0000', 0.996108949416, 8.0, 0)
    hl.highlight(2000)
    gtk.main()

