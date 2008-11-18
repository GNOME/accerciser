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
import gtk
import gtk.gdk
import pyatspi
import gobject
import string
import rsvg
import cairo
from tools import Tools, parseColorString
import gconf

MAX_BLINKS = 6

cl = gconf.client_get_default()
BORDER_COLOR, BORDER_ALPHA = parseColorString(
  cl.get_string('/apps/accerciser/highlight_border') or '#ff0000ff') 

FILL_COLOR, FILL_ALPHA  = parseColorString(
  cl.get_string('/apps/accerciser/highlight_fill') or '#ff00006f')

HL_DURATION = int(cl.get_float('/apps/accerciser/highlight_duration')*1000)

class Bag(object):
  '''
  Bag class for converting a dicionary to an object with attributes.
  '''
  def __init__(self, **kwargs):
    self.__dict__.update(kwargs)
    
  def __str__(self):
    return ', '.join(vars(self).keys())

class Node(gobject.GObject, Tools):
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
                  (gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, 
                   (gobject.TYPE_PYOBJECT,)),
                  'blink-done' : 
                  (gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, 
                   ())}
  def __init__(self):
    self.desktop = pyatspi.Registry.getDesktop(0)
    self.acc = None
    self.extents = None
    self.tree_path = None
    gobject.GObject.__init__(self)
    
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
    display = gtk.gdk.display_get_default()
    screen = display.get_default_screen()
    self.root = screen.get_root_window()
    self.gc = self.root.new_gc()
    self.gc.set_subwindow(gtk.gdk.INCLUDE_INFERIORS)
    self.gc.set_function(gtk.gdk.INVERT)
    self.gc.set_line_attributes(3, gtk.gdk.LINE_ON_OFF_DASH, gtk.gdk.CAP_BUTT, 
                                gtk.gdk.JOIN_MITER)
    self.inv = gtk.Invisible()
    self.inv.set_screen(screen)
    gobject.timeout_add(30, self._drawRectangle)

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
  _svg = r"""
<svg width="100%" height="100%" version="1.1"
  xmlns="http://www.w3.org/2000/svg">
  <rect x="$x" y="$y" width="$width" height="$height"
      style="fill:$fill;stroke-width:$stroke_width;stroke:$stroke;
      fill-opacity:$fill_opacity;stroke-opacity:$stroke_opacity"
      rx="2" ry="2"
      />
</svg>
"""
  def __init__(self, x, y, w, h, 
               fill_color, fill_alpha,
               stroke_color, stroke_alpha, 
               stroke_width, padding=0):

    # Initialize window.
    gtk.Window.__init__(self, gtk.WINDOW_POPUP)

    # Normalize position for stroke and padding.
    self.x, self.y = x - padding, y - padding
    self.w, self.h = w + padding*2, h + padding*2

    # Determine if we are compositing.
    self._composited = self.is_composited()
    if self._composited:
      # Prepare window for transparency.
      screen = self.get_screen()
      colormap = screen.get_rgba_colormap()
      self.set_colormap(colormap)
    else:
      # Take a screenshot for compositing on the client side.
      self.root = gtk.gdk.get_default_root_window().get_image(
        self.x, self.y, self.w, self.h)

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

    # Connect "expose" event.
    self.connect("expose-event", self._onExpose)
    
  def highlight(self, duration=500):
    if duration > 0:
      gobject.timeout_add(duration, lambda w: w.destroy(), self)
      self.show_all()
    else:
      self.destroy()
    

  def _onExpose(self, widget, event):
    svgh = rsvg.Handle()
    try:
      svgh.write(self.svg)
    except (gobject.GError, KeyError, ValueError), ex:
      print 'Error reading SVG for display: %s\r\n%s', ex, self.svg
      svgh.close()
      return
    svgh.close()
      
    if not self._composited:
      # Draw the screengrab of the underlaying window, and set the drawing
      # operator to OVER.
      self.window.draw_image(self.style.black_gc, self.root, 
                             event.area.x,event.area.y, 
                             event.area.x, event.area.y, 
                             event.area.width, event.area.height)
      cairo_operator = cairo.OPERATOR_OVER
    else:
      cairo_operator = cairo.OPERATOR_SOURCE
    cr = self.window.cairo_create()
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
    cr.set_operator(cairo_operator)
    cr.paint()

    svgh.render_cairo( cr )
    del svgh
