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
import new
import gconf

class Tools(object):
  '''
  A class with some common methods that more than a few classes will need.

  @cvar SETTINGS_PATH: Directory in which the L{SETTINGS_FILE} resides.
  @type SETTINGS_PATH: string
  @cvar SETTINGS_FILE: The file that contains information we with to persist
  across session.
  @type SETTINGS_FILE: string
  @ivar my_app_id: Unique L{pyLinAcc.Interfaces.IApplication} ID of current 
  instance.
  @type my_app_id: integer
  '''  

  def isMyApp(self, acc):
    '''
    Checks if a given L{pyLinAcc.Accessible} belongs to this current
    app instance. This is useful for avoiding recursion and such.

    @param acc: The given L{pyLinAcc.Accessible} to check.
    @type acc: L{pyLinAcc.Accessible}
    @return: True if L{acc} is a member of current app instance.
    @rtype: boolean
    '''
    if not acc:
      return False
    try:
      app = acc.getApplication()
    except Exception, e:
      return False
    if not app or not hasattr(app, 'id'):
      return False
    if hasattr(self,'my_app_id'):
      if self.my_app_id == app.id:
        return True
    else:
      if app.description == str(os.getpid()):
        self.my_app_id = app.id
        return True
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
      return None
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

class GConfListWrapper(object):
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
    obj = self.CallWrapper(name, self.gconf_key)
    return obj(*args, **kwargs)
  def __getattr__(self, name):
    obj = getattr(self.wrapped_list, name)
    if callable(obj):
      return self.CallWrapper(name, self.gconf_key)
    else:
      return obj
    
  class CallWrapper(object):
    def __init__ (self, name, gconf_key):
      self.name = name
      self.gconf_key = gconf_key
    def __call__(self, *args, **kwargs):
      cl = gconf.client_get_default()
      l = cl.get_list(self.gconf_key, 
                      gconf.VALUE_STRING)
      rv = getattr(l, self.name)(*args, **kwargs)
      cl.set_list(self.gconf_key, 
                  gconf.VALUE_STRING, l)
      return rv
