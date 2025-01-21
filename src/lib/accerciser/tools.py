'''
Defines a base class having tools common to the core and the plugins.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2006, 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''
import os
import pickle
import weakref

import traceback
import functools

class Tools(object):
  '''
  A class with some common methods that more than a few classes will need.

  @ivar pid: Process ID of current Accerciser instance.
  @type pid: integer
  '''

  def isMyApp(self, acc):
    '''
    Checks if a given L{Accessibility.Accessible} belongs to this current
    app instance. This is useful for avoiding recursion and such.

    @param acc: The given L{Accessibility.Accessible} to check.
    @type acc: L{Accessibility.Accessible}
    @return: True if L{acc} is a member of current app instance.
    @rtype: boolean
    '''
    if not hasattr(self, 'pid'):
      self.pid = os.getpid()

    if not acc:
      return False
    try:
      app = acc.get_application()
      # check whether PID is set as description, set in Main.do_startup
      return app.get_description() == str(self.pid)
    except Exception as e:
      return False


class Proxy(object):
  '''
  Our own proxy object which enables weak references to bound and unbound
  methods and arbitrary callables. Pulls information about the function,
  class, and instance out of a bound method. Stores a weak reference to the
  instance to support garbage collection.
  '''
  def __init__(self, cb):
    try:
      try:
        self.inst = weakref.ref(cb.__self__)
      except TypeError:
        self.inst = None
      self.func = cb.__func__
      self.klass = cb.__self__.__class__
    except AttributeError:
      self.inst = None
      self.func = cb.__func__
      self.klass = None

  def __call__(self, *args, **kwargs):
    '''
    Proxy for a call to the weak referenced object. Take arbitrary params to
    pass to the callable.

    @raise ReferenceError: When the weak reference refers to a dead object
    '''
    if self.inst is not None and self.inst() is None:
      return
    elif self.inst is not None:
      # build a new instance method with a strong reference to the instance
      mtd = self.func.__get__(self.inst(), self.klass)
    else:
      # not a bound method, just return the func
      mtd = self.func
    # invoke the callable and return the result
    return mtd(*args, **kwargs)

  def __eq__(self, other):
    '''
    Compare the held function and instance with that held by another proxy.

    @param other: Another proxy object
    @type other: L{Proxy}
    @return: Whether this func/inst pair is equal to the one in the other proxy
      object or not
    @rtype: boolean
    '''
    try:
      return self.func == other.func and self.inst() == other.inst()
    except Exception:
      return False

  def __ne__(self, other):
    '''
    Inverse of __eq__.
    '''
    return not self.__eq__(other)

def parseColorString(color_string):
  '''
  Parse a string representation of a 24-bit color, and a 8 bit alpha mask.

  @param color_string: String in the format: #rrbbggaa.
  @type color_string: string

  @return: A color string in the format of #rrggbb, and an opacity value
  of 0.0 to 1.0
  @rtype: tuple of string and float.
  '''
  return color_string[:-2], int(color_string[-2:], 16)/255.0

def getTreePathBoundingBox(treeview, path, col):
  '''
  Get bounding box of given tree path.
  '''
  gdkwindow = treeview.window
  x, y = treeview.allocation.x, treeview.allocation.y
  while gdkwindow:
    window_x, window_y = gdkwindow.get_position()
    x += window_x
    y += window_y
    gdkwindow = gdkwindow.get_parent()
  rect = treeview.get_cell_area(path, col)
  rect.x, rect.y = treeview.tree_to_widget_coords(rect.x, rect.y)
  rect.x += x
  rect.y += y
  return rect

def logException(func):
  '''
  Handle (and log) the exceptions that are coming from plugins
  '''
  @functools.wraps(func)
  def newfunc(*args, **kwargs):
    # use Exception otherwise KeyboardInterrupt won't get through
    try:
      return func(*args, **kwargs)
    except Exception:
      traceback.print_exc()
  return newfunc

class ToolsAccessor(Tools):
  '''
  By following the recommendation on
  https://bugzilla.gnome.org/show_bug.cgi?id=723081#c4, this Accessor allows us
  to wrap every plugin's method and in order to catch all possible exceptions
  and print them appropiately.
  '''
  def __init__(self, plugin):
    self.plugin = plugin

    @logException
    def method(self):
      return self.plugin.method()
