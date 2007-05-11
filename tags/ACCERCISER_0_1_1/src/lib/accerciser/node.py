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
import pyLinAcc
import gobject
from tools import Tools

MAX_BLINKS = 4

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
  application L{pyLinAcc.Accessible}s
  @type desktop: L{pyLinAcc.Accessible}
  @ivar acc: The currently selected accessible.
  @type acc: L{pyLinAcc.Accessible}
  @ivar extents: The extents of a given accessible.
  @type extents: L{Bag}
  '''
  __gsignals__ = {'accessible_changed' : 
                  (gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, 
                   (gobject.TYPE_PYOBJECT,))}
  def __init__(self):
    self.__dict__.update(pyLinAcc.Interfaces.__dict__)
    self.__dict__.update(pyLinAcc.Constants.__dict__)
    self.desktop = pyLinAcc.Registry.getDesktop(0)
    self.acc = None
    self.extents = None
    gobject.GObject.__init__(self)
    
  def update(self, acc):
    '''
    Updates the information in this node for the given accessible including 
    a reference to the accessible and its extents. Also emit the 
    'accessible-changed' signal.

    @param acc: An accessible.
    @type acc: L{pyLinAcc.Accessible}
    '''
    if not acc or self.isMyApp(acc):
      return
    self.acc = acc
    try:
      i = pyLinAcc.Interfaces.IComponent(acc)
    except NotImplementedError:
      self.extents = Bag(x=0, y=0, width=0, height=0)
    else:
      self.extents = i.getExtents(pyLinAcc.Constants.DESKTOP_COORDS)
    self.blinkRect()
    self.emit('accessible_changed', acc)
  
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
      return False
    return True

