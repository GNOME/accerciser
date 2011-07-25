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
from gi.repository import GConf as gconf

import os
import pickle
import weakref
import new

class Tools(object):
  '''
  A class with some common methods that more than a few classes will need.

  @cvar SETTINGS_PATH: Directory in which the L{SETTINGS_FILE} resides.
  @type SETTINGS_PATH: string
  @cvar SETTINGS_FILE: The file that contains information we with to persist
  across session.
  @type SETTINGS_FILE: string
  @ivar my_app_id: Unique L{Accessibility.Application} ID of current 
  instance.
  @type my_app_id: integer
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
    if not acc:
      return False
    try:
      app = acc.getApplication()
    except Exception, e:
      return False
    try:
      app_id = app.id
    except:
      return False
    if hasattr(self,'my_app_id'):
      if self.my_app_id == app_id:
        return True
    else:
      if app.description == str(os.getpid()):
        self.my_app_id = app_id
        return True
    return False
  
class GConfListWrapper(object):
  '''
  Wrapper for gconf list types. It keeps the list stateless, and updates
  gconf on every list change.
  '''
  def __init__(self, key):
    self.gconf_key = key
    self.wrapped_list = []
  def __str__(self):
    return self._wrap('__str__')
  def __iter__(self):
    return self._wrap('__iter__')
  def __repr__(self):
    return self._wrap('__repr__')
  def __len__(self):
    return self._wrap('__len__')
  def __getitem__(self, key):
    return self._wrap('__getitem__', key)
  def __setitem__(self, key, value):
    return self._wrap('__setitem__', key, value)
  def __delitem__(self, key):
    return self._wrap('__delitem__', key)
  def __getslice__(self, i, j):
    return self._wrap('__getslice__', i, j)
  def __setslice__(self, i, j, sequence):
    return self._wrap('__setslice__', i, j, sequence)
  def __delslice__(self, i, j):
    return self._wrap('__delslice__', i, j)
  def _wrap(self, name, *args, **kwargs):
    obj = self._CallWrapper(name, self.gconf_key)
    return obj(*args, **kwargs)
  def __getattr__(self, name):
    obj = getattr(self.wrapped_list, name)
    if callable(obj):
      return self._CallWrapper(name, self.gconf_key)
    else:
      return obj
    
  class _CallWrapper(object):
    '''
    Does the actual wrapping.
    '''
    def __init__ (self, name, gconf_key):
      self.name = name
      self.gconf_key = gconf_key
    def __call__(self, *args, **kwargs):
      cl = gconf.Client.get_default()
      # pygtk-pygi ISSUE
      # get_list instrospectio mark isn't properly done?
      #
      #l = cl.get_list(self.gconf_key, 
      #                gconf.VALUE_STRING)
      l = cl.get(self.gconf_key).get_list()
      rv = getattr(l, self.name)(*args, **kwargs)
      cl.set_list(self.gconf_key, 
                  gconf.ValueType.STRING, l)
      return rv

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
        self.inst = weakref.ref(cb.im_self)
      except TypeError:
        self.inst = None
      self.func = cb.im_func
      self.klass = cb.im_class
    except AttributeError:
      self.inst = None
      self.func = cb.im_func
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
      mtd = new.instancemethod(self.func, self.inst(), self.klass)
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
  return color_string[:-2], long(color_string[-2:], 16)/255.0

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
