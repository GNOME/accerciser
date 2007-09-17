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
from tools import Tools

MAX_BLINKS = 6

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
    self.blinkRect()
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

