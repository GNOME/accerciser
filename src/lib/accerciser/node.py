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
from gi.repository.Gio import Settings as GSettings
gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg as rsvg
import cairo
import pyatspi
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
  @ivar window_manager: The window manager.
  @type window_manager: L{WindowManager}
  '''
  __gsignals__ = {'accessible-changed' :
                  (GObject.SignalFlags.RUN_FIRST,
                   None,
                   (GObject.TYPE_PYOBJECT,))}
  def __init__(self, window_manager):
    self.desktop = pyatspi.Registry.getDesktop(0)
    self.acc = None
    self.tree_path = None
    self.window_manager = window_manager
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

  def highlight(self):
    extents = self.window_manager.getScreenExtents(self.acc)
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
    screen = self.get_screen()
    self._composited = screen.is_composited()
    if self._composited:
      # Prepare window for transparency.
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
    self.connect("draw", self._onDraw)

  def highlight(self, duration=500):
    if duration > 0:
      GLib.timeout_add(duration, lambda w: w.destroy(), self)
      self.show_all()
    else:
      self.destroy()

  def _onDraw(self, widget, cr):
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
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
    cr.set_operator(cairo_operator)

    rect = rsvg.Rectangle()
    rect.x = 0
    rect.y = 0
    rect.width = self.w
    rect.height = self.h

    svgh.render_document(cr, rect)
    del svgh

if __name__ == "__main__":
    hl = _HighLight(200, 200, 200, 200, '#ff0000',
                    0.5, '#ff0000', 0.996108949416, 8.0, 0)
    hl.highlight(2000)
    gtk.main()

