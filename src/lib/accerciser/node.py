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
#from gi.repository import cairo
import cairo
import pyatspi
import string
from .tools import Tools, parseColorString

MAX_BLINKS = 6

gsettings = GSettings(schema='org.a11y.Accerciser')
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

class Node(GObject.GObject, Tools):
  '''
  Node class that contains convient references to accessibility information 
  for the currently selected node. A L{Node} instance will emit an 
  'accessible-changed' signal when L{update} is called with a new accessible.

  @ivar desktop: The desktop accessible. It holds references to all the 
  application L{Accessibility.Accessible}s
  @type desktop: L{Accessibility.Accessible}
  @ivar acc: The currently selected accessible.
  @type acc: L{Accessibility.Accessible}
  @ivar extents: The extents of a given accessible.
  @type extents: L{Bag}
  '''
  __gsignals__ = {'accessible-changed' : 
                  (GObject.SignalFlags.RUN_FIRST,
                   None, 
                   (GObject.TYPE_PYOBJECT,)),
                  'blink-done' : 
                  (GObject.SignalFlags.RUN_FIRST,
                   None, 
                   ())}
  def __init__(self):
    self.desktop = pyatspi.Registry.getDesktop(0)
    self.acc = None
    self.extents = None
    self.tree_path = None
    GObject.GObject.__init__(self)
    
  def update(self, acc):
    '''
    Updates the information in this node for the given accessible including 
    a reference to the accessible and its extents. Also emit the 
    'accessible-changed' signal.

    @param acc: An accessible.
    @type acc: L{Accessibility.Accessible}
    '''
    if not acc or self.isMyApp(acc):
      return
    self.acc = acc
    self.extents = Bag(x=0, y=0, width=0, height=0)
    try:
      i = acc.queryComponent()
    except NotImplementedError:
      pass
    else:
      if isinstance(i, pyatspi.Accessibility.Component):
        self.extents = i.getExtents(pyatspi.DESKTOP_COORDS)
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
    if self.extents is None or \
          0 in (self.extents.width, self.extents.height) or \
          -0x80000000 in (self.extents.x, self.extents.y):
      return
    ah = _HighLight(self.extents.x, self.extents.y, 
                    self.extents.width, self.extents.height, 
                    FILL_COLOR, FILL_ALPHA, BORDER_COLOR, BORDER_ALPHA, 
                    2.0, 0)
    ah.highlight(HL_DURATION)

  def blinkRect(self, times=MAX_BLINKS):
    '''
    Blink a rectangle on the screen using L{extents} for position and size.

    @param times: Maximum times to blink.
    @type times: integer
    '''
    if self.extents is None or \
          -0x80000000 in (self.extents.x, self.extents.y):
      return
    self.max_blinks = times
    self.blinks = 0
    # get info for drawing higlight rectangles
    display = gdk.Display.get_default()
    screen = display.get_default_screen()
    self.root = screen.get_root_window()
    self.gc = self.root.new_gc()
    self.gc.set_subwindow(gdk.SubwindowMode.INCLUDE_INFERIORS)
    self.gc.set_function(gdk.Function.INVERT)
    self.gc.set_line_attributes(3, gdk.LineStyle.ON_OFF_DASH, \
                                gdk.CapStyle.BUTT, gdk.JoinStyle.MITER)
    self.inv = gtk.Invisible()
    self.inv.set_screen(screen)
    GLib.timeout_add(30, self._drawRectangle)

  def _drawRectangle(self):
    '''
    Draw a rectangle on the screen using L{extents} for position and size.
    '''
    # draw a blinking rectangle 
    if self.blinks == 0:
      self.inv.show()
      self.inv.grab_add()
    self.root.draw_rectangle(self.gc, False, 
                             self.extents.x,
                             self.extents.y,
                             self.extents.width,
                             self.extents.height)
    self.blinks += 1
    if self.blinks >= self.max_blinks:
      self.inv.grab_remove()
      self.inv.destroy()
      self.emit('blink-done')
      return False
    return True


class _HighLight(gtk.Window):
  '''
  Highlight box class. Uses compositing when available. When not, it does
  transparency client-side.
  '''
  def __init__(self, x, y, w, h, 
               fill_color, fill_alpha,
               stroke_color, stroke_alpha, 
               stroke_width, padding=0):

    # Initialize window.
    #gtk.Window.__init__(self, gtk.WindowType.POPUP)
    gtk.Window.__init__(self)

    # Normalize position for stroke and padding.
    self.x, self.y = x - padding, y - padding
    self.w, self.h = w + padding*2, h + padding*2
    self.fill_color = fill_color

    # TODO: Implement transparency for fallback-mode
    #
    # Determine if we are compositing.
    #self._composited = self.is_composited()
    #if self._composited:
    #  # Prepare window for transparency.
    #  screen = self.get_screen()
    #  visual = screen.get_rgba_visual()
    #  self.set_visual(visual)
    #else:
    #  # Take a screenshot for compositing on the client side.
    #  self.root = gdk.get_default_root_window().get_image(
    #    self.x, self.y, self.w, self.h)
    #  #self.root = gtk.Image(self.x, self.y, self.w, self.h)
 

    # Place window, and resize it, and set proper properties.
    self.set_app_paintable(True)
    self.set_decorated(False)
    self.set_keep_above(True)
    self.move(self.x, self.y)
    self.resize(self.w, self.h)
    self.set_accept_focus(False)
    self.set_sensitive(False)
    self.set_opacity(fill_alpha)

#    # Create SVG with given parameters.
#    offset = stroke_width/2.0
#    self.svg = string.Template(self._svg).substitute(
#      x=offset, y=offset,
#      width=int(self.w - stroke_width), height=int(self.h - stroke_width),
#      fill=fill_color, 
#      stroke_width=stroke_width,
#      stroke=stroke_color,
#      fill_opacity=fill_alpha,
#      stroke_opacity=stroke_alpha)

    da = gtk.DrawingArea()
    # Connect "draw"
    da.connect("draw", self._onExpose)
    self.add(da)
    self.show_all()
    
  def highlight(self, duration=500):
    if duration > 0:
      GLib.timeout_add(duration, lambda w: w.destroy(), self)
      self.show_all()
    else:
      self.destroy()
    
  def _onExpose(self, widget, event):
    window = widget.get_window()
    cr = window.cairo_create()

    if not self.is_composited():
      # Draw the screengrab of the underlaying window, and set the drawing
      # operator to OVER.
      #self.window.draw_image(self.style.black_gc, self.root,
      #                       event.area.x,event.area.y,
      #                       event.area.x, event.area.y,
      #                       event.area.width, event.area.height)
      cairo_operator = cairo.OPERATOR_OVER
    else:
      cairo_operator = cairo.OPERATOR_SOURCE
    cr.set_operator(cairo_operator)

    color = gdk.color_parse(self.fill_color)

    #TODO: look for for set_source_rgb and Gdk.Color issues
    #
    cr.set_source_rgb(color.red, color.green, color.blue)
    cr.paint()


#class _HighLight(gtk.Window):
#  '''
#  Highlight box class. Uses compositing when available. When not, it does
#  transparency client-side.
#  '''
#  _svg = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
#<svg xmlns="http://www.w3.org/2000/svg"> 
#  <rect
#       style="fill:$fill;fill-opacity:$fill_opacity;fill-rule:evenodd;stroke:$stroke;stroke-width:2;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-dasharray:none;stroke-opacity:$stroke_opacity"
#       id="highlight"
#       width="$width"
#       height="$height"
#       x="$x"
#       y="$y"
#       rx="2"
#       ry="2" />
#</svg>
#"""
#  def __init__(self, x, y, w, h, 
#               fill_color, fill_alpha,
#               stroke_color, stroke_alpha, 
#               stroke_width, padding=0):
#
#    # Initialize window.
#    #gtk.Window.__init__(self, gtk.WindowType.POPUP)
#    gtk.Window.__init__(self)
#
#    # Normalize position for stroke and padding.
#    self.x, self.y = x - padding, y - padding
#    self.w, self.h = w + padding*2, h + padding*2
#
#    # Determine if we are compositing.
#    self._composited = self.is_composited()
#    if self._composited:
#      # Prepare window for transparency.
#      screen = self.get_screen()
#      visual = screen.get_rgba_visual()
#      self.set_visual(visual)
#    else:
#      # Take a screenshot for compositing on the client side.
#      self.root = gdk.get_default_root_window().get_image(
#        self.x, self.y, self.w, self.h)
#
#    # Place window, and resize it, and set proper properties.
#    self.set_app_paintable(True)
#    self.set_decorated(False)
#    self.set_keep_above(True)
#    self.move(self.x, self.y)
#    self.resize(self.w, self.h)
#    self.set_accept_focus(False)
#    self.set_sensitive(False)
#
#    # Create SVG with given parameters.
#    offset = stroke_width/2.0
#    self.svg = string.Template(self._svg).substitute(
#      x=offset, y=offset,
#      width=int(self.w - stroke_width), height=int(self.h - stroke_width),
#      fill=fill_color, 
#      stroke_width=stroke_width,
#      stroke=stroke_color,
#      fill_opacity=fill_alpha,
#      stroke_opacity=stroke_alpha)
#
#    # Connect "draw"
#    self.connect("draw", self._onExpose)
#    
#  def highlight(self, duration=500):
#    if duration > 0:
#      GLib.timeout_add(duration, lambda w: w.destroy(), self)
#      self.show_all()
#    else:
#      self.destroy()
#    
#  def _onExpose(self, widget, event):
#    svgh = rsvg.Handle()
#    try:
#      svgh.write(self.svg)
#    except (GObject.GError, KeyError, ValueError), ex:
#      print 'Error reading SVG for display: %s\r\n%s', ex, self.svg
#      svgh.close()
#      return
#    svgh.close()
#      
#    if not self._composited:
#      # Draw the screengrab of the underlaying window, and set the drawing
#      # operator to OVER.
#      self.window.draw_image(self.style.black_gc, self.root, 
#                             event.area.x,event.area.y, 
#                             event.area.x, event.area.y, 
#                             event.area.width, event.area.height)
#      cairo_operator = cairo.OPERATOR_OVER
#    else:
#      cairo_operator = cairo.OPERATOR_SOURCE
#    window = self.get_window()
#    cr = window.cairo_create()
#    cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
#    cr.set_operator(cairo_operator)
#    cr.paint()
#
#    svgh.render_cairo( cr )
#    del svgh

if __name__ == "__main__":
    hl = _HighLight(200, 200, 200, 200, '#ff0000', 
                    0.5, '#ff0000', 0.996108949416, 8.0, 0)
    hl.highlight(2000)
    gtk.main()

