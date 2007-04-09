'''
Creates functions at import time that are mixed into the 
Accessibility.Accessible base class to make it more Pythonic.

Based on public domain code originally posted at 
http://wwwx.cs.unc.edu/~parente/cgi-bin/RuntimeClassMixins.

@todo: PP: also need to mix into methods in StateSet and other objects a client
  might receive
@todo: PP: investigate caching; possible hitch with __slots__

@author: Peter Parente
@organization: IBM Corporation
@copyright: Copyright (c) 2005, 2007 IBM Corporation
@license: The BSD License

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD license which accompanies
this distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import new
import types
import ORBit
import Accessibility
import constants
import utils

def _makeQuery(idl):
  '''
  Builds a function querying to a specific interface and returns it.
  
  @ivar idl: Interface identifier to use when querying
  @type idl: string
  @return: Function querying to the given interface
  @rtype: function
  '''
  def _inner(self):
    '''
    Queries an object for another interface.
  
    @return: An object with the desired interface
    @rtype: object
    @raise NotImplementedError: When the desired interface is not supported
    '''
    try:
      i = self.queryInterface(idl)
    except Exception:
      raise NotImplementedError
    if i is None:
      raise NotImplementedError
    else:
      # not needed according to ORBit2 spec, but makes Java queries work
      # more reliably according to Orca experience
      i._narrow(i.__class__)
    return i
  return _inner

def _makeExceptionHandler(func):
  '''
  Builds a function calling the one it wraps in try/except statements catching
  CORBA exceptions.
  
  @return: Function calling the method being wrapped
  @rtype: function
  '''
  def _inner(self, *args, **kwargs):
    try:
      # try calling the original func
      return func(self, *args, **kwargs)
    except ORBit.CORBA.NO_IMPLEMENT, e:
      # raise Python exception
      raise NotImplementedError(e)
    except ORBit.CORBA.Exception, e:
      # raise Python exception
      raise LookupError(e)
  return _inner

def _mixInterfaces(cls, interfaces):
  '''
  Add methods for querying to interfaces other than the base accessible to
  the given class.
  
  @param cls: Class to mix interface methods into
  @type cls: class
  @param interfaces: Classes representing AT-SPI interfaces
  @type interfaces: list of class
  '''
  # create functions in this module for all interfaces listed in constants
  for interface in interfaces:
    # build name of converter from the name of the interface
    name = 'query%s' % utils.getInterfaceName(interface)
    # build a function that queries to the given interface
    func = _makeQuery(utils.getInterfaceIID(interface))
    # build a new method that is a clone of the original function
    method = new.function(func.func_code, func.func_globals, name, 
                          func.func_defaults, func.func_closure)
    # add the method to the given class
    setattr(cls, name, method)

def _mixExceptions(cls):
  '''
  Wraps all methods and properties in a class with handlers for CORBA 
  exceptions.
  
  @param cls: Class to mix interface methods into
  @type cls: class
  '''
  # loop over all names in the new class
  for name in cls.__dict__.keys():
    obj = cls.__dict__[name]
    # check if we're on a protected or private method
    if name.startswith('_'):
      continue
    # check if we're on a method
    elif isinstance(obj, types.FunctionType):
      # wrap the function in an exception handler
      method = _makeExceptionHandler(obj)
      # add the wrpped function to the class
      setattr(cls, name, method)
    # check if we're on a property
    elif isinstance(obj, property):
      # wrap the getters and setters
      if obj.fget:
        getter = _makeExceptionHandler(obj.fget)
      else:
        getter = None
      if obj.fset:
        setter = _makeExceptionHandler(obj.fset)
      else:
        setter = None
      setattr(cls, name, property(getter, setter))

def _mixClass(cls, new_cls):
  '''  
  Adds the methods in new_cls to cls. After mixing, all instances of cls will
  have the new methods. If there is a method name clash, the method already in
  cls will be prefixed with an underscore before the new method of the same
  name is mixed in.

  @param cls: Existing class to mix features into
  @type cls: class
  @param new_cls: Class containing features to add
  @type new_cls: class
  '''       
  # loop over all names in the new class
  for name in new_cls.__dict__.keys():
    # get only functions from the new_class
    if isinstance(new_cls.__dict__[name], types.FunctionType):
      # get the function from the new_cls
      func = new_cls.__dict__[name]
      # build a new function that is a clone of the one from new_cls
      method = new.function(func.func_code, func.func_globals, name, 
                            func.func_defaults, func.func_closure)
      try:
        # check if a method of the same name already exists in the target
        old_method = getattr(cls, name)
      except AttributeError:
        pass
      else:
        # rename the old method so we can still call it if need be
        setattr(cls, '_'+name, old_method)
      # add the clone to cls
      setattr(cls, name, method)

class _AccessibleMixin(object):
  '''
  Defines methods to be added to the Accessibility.Accessible class. The
  features defined here will be added to the Accessible class at run time so
  that all instances of Accessible have them (i.e. there is no need to
  explicitly wrap an Accessible in this class or derive a new class from it.)
  '''
  def __del__(self):
    '''
    Decrements the reference count on the accessible object when there are no
    Python references to this object. This provides automatic reference 
    counting for AT-SPI objects.
    '''
    try:
      self.unref()
    except Exception:
      pass
    
  def __iter__(self):
    '''
    Iterator that yields one accessible child per iteration. If an exception is
    encountered, None is yielded instead.
    
    @return: A child accessible
    @rtype: Accessibility.Accessible
    '''
    for i in xrange(self.childCount):
      try:
        yield self.getChildAtIndex(i)
      except constants.CORBAException:
        yield None
    
  def __str__(self):
    '''
    Gets a human readable representation of the accessible.
    
    @return: Role and name information for the accessible
    @rtype: string
    '''
    try:
      return '[%s | %s]' % (self.getRoleName(), self.name)
    except Exception:
      return '[DEAD]'
    
  def __nonzero__(self):
    '''
    @return: True, always
    @rtype: boolean
    '''
    return True
    
  def __getitem__(self, index):
    '''
    Thin wrapper around getChildAtIndex.
    
    @param index: Index of desired child
    @type index: integer
    @return: Accessible child
    @rtype: Accessibility.Accessible
    '''
    return self.getChildAtIndex(index)
  
  def __len__(self):
    '''
    Thin wrapper around childCount.
    
    @return: Number of child accessibles
    @rtype: integer
    '''
    return self.childCount
    
  def getIndexInParent(self):
    '''
    Gets the index of this accessible in its parent. Uses the implementation of
    this method provided by the Accessibility.Accessible object, but checks the
    bound of the value to ensure it is not outside the range of childCount 
    reported by this accessible's parent.
    
    @return: Index of this accessible in its parent
    @rtype: integer
    '''
    i = self._getIndexInParent()
    try:
      # correct for out-of-bounds index reporting
      return min(self.parent.childCount-1, i)
    except AttributeError:
      # return sentinel if there is no parent
      return -1

  def getApplication(self):
    '''
    Gets the most-parent accessible (the application) of this accessible. Tries 
    using the getApplication method introduced in AT-SPI 1.7.0 first before 
    resorting to traversing parent links.
    
    @warning: Cycles involving more than the previously traversed accessible 
      are not detected by this code.
    @return: Application object
    @rtype: Accessibility.Application
    '''
    try:
      return self._getApplication()
    except AttributeError:
      pass
    curr = self
    try:
      while curr.parent is not None and (not curr.parent == curr):
        curr = curr.parent
      return curr
    except Exception:
      pass
    # return None if the application isn't reachable for any reason
    return None
  
# mix the new functions
_mixClass(Accessibility.Accessible, _AccessibleMixin)
# mix queryInterface convenience methods
_mixInterfaces(Accessibility.Accessible, constants.ALL_INTERFACES)
# mix the exception handlers into all queryable interfaces
map(_mixExceptions, constants.ALL_INTERFACES)
# mix the exception handlers into other Accessibility objects
map(_mixExceptions, [Accessibility.StateSet])
