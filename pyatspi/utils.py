'''
Utility functions for AT-SPI for querying interfaces, searching the hierarchy,
converting constants to strings, and so forth.

@author: Peter Parente
@organization: IBM Corporation
@copyright: Copyright (c) 2005, 2007 IBM Corporation
@license: The BSD License

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD license which accompanies
this distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import Accessibility__POA

def getInterfaceIID(cls):
  '''
  Gets the ID of an interface class in string format for use in queryInterface.
  
  @param cls: Class representing an AT-SPI interface
  @type cls: class
  @return: IID for the interface
  @rtype: string
  @raise AttributeError: When the parameter does not provide typecode info
  '''
  return cls.__typecode__.repo_id

def getInterfaceName(cls):
  '''
  Gets the human readable name of an interface class in string format.
  
  @param cls: Class representing an AT-SPI interface
  @type cls: class
  @return: Name of the interface
  @rtype: string
  @raise AttributeError: When the parameter does not provide typecode info
  '''
  return cls.__typecode__.name

# we're importing here to avoid cyclic importants; constants relies on the
# two functions above
import constants

def stringToConst(prefix, suffix):
  '''
  Maps a string name to an AT-SPI constant. The rules for the mapping are as 
  follows:
    - The prefix is captalized and has an _ appended to it.
    - All spaces in the suffix are mapped to the _ character. 
    - All alpha characters in the suffix are mapped to their uppercase.
    
  The resulting name is used with getattr to look up a constant with that name
  in the L{constants} module. If such a constant does not exist, the string
  suffix is returned instead.

  This method allows strings to be used to refer to roles, relations, etc. 
  without direct access to the constants. It also supports the future expansion
  of roles, relations, etc. by allowing arbitrary strings which may or may not
  map to the current standard set of roles, relations, etc., but may still match
  some non-standard role, relation, etc. being reported by an application.
  
  @param prefix: Prefix of the constant name such as role, relation, state, 
    text, modifier, key
  @type prefix: string
  @param suffix: Name of the role, relation, etc. to use to lookup the constant
  @type suffix: string
  @return: The matching constant value
  @rtype: object
  '''
  name = prefix.upper()+'_'+suffix.upper().replace(' ', '_')
  return getattr(constants, name, suffix)

def stateToString(value):
  '''
  Converts a state value to a string based on the name of the state constant in 
  the L{constants} module that has the given value.
  
  @param value: An AT-SPI state
  @type value: Accessibility.StateType
  @return: Human readable, untranslated name of the state
  @rtype: string
  '''
  return constants.STATE_VALUE_TO_NAME.get(value)

def relationToString(value):
  '''
  Converts a relation value to a string based on the name of the state constant
  in the L{constants} module that has the given value.
  
  @param value: An AT-SPI relation
  @type value: Accessibility.RelationType
  @return: Human readable, untranslated name of the relation
  @rtype: string
  '''
  return constants.RELATION_VALUE_TO_NAME.get(value)

def allModifiers():
  '''
  Generates all possible keyboard modifiers for use with 
  L{registry.Registry.registerKeystrokeListener}.
  '''
  mask = 0
  while mask <= (1 << constants.MODIFIER_NUMLOCK):
    yield mask
    mask += 1

def findDescendant(acc, pred, breadth_first=False):
  '''
  Searches for a descendant node satisfying the given predicate starting at 
  this node. The search is performed in depth-first order by default or
  in breadth first order if breadth_first is True. For example,
  
  my_win = findDescendant(lambda x: x.name == 'My Window')
  
  will search all descendants of node until one is located with the name 'My
  Window' or all nodes are exausted. Calls L{_findDescendantDepth} or
  L{_findDescendantBreadth} to start the recursive search.
  
  @param acc: Root accessible of the search
  @type acc: Accessibility.Accessible
  @param pred: Search predicate returning True if accessible matches the 
      search criteria or False otherwise
  @type pred: callable
  @param breadth_first: Search breadth first (True) or depth first (False)?
  @type breadth_first: boolean
  @return: Accessible matching the criteria or None if not found
  @rtype: Accessibility.Accessible or None
  '''
  if breadth_first:
    return _findDescendantBreadth(acc, pred)

  for child in acc:
    try:
      ret = _findDescendantDepth(acc, pred)
    except Exception:
      ret = None
    if ret is not None: return ret

def _findDescendantBreadth(acc, pred):
  '''    
  Internal function for locating one descendant. Called by L{findDescendant} to
  start the search.
  
  @param acc: Root accessible of the search
  @type acc: Accessibility.Accessible
  @param pred: Search predicate returning True if accessible matches the 
      search criteria or False otherwise
  @type pred: callable
  @return: Matching node or None to keep searching
  @rtype: Accessibility.Accessible or None
  '''
  for child in acc:
    try:
      if pred(child): return child
    except Exception:
      pass
  for child in acc:
    try:
      ret = _findDescedantBreadth(child, pred)
    except Exception:
      ret = None
    if ret is not None: return ret

def _findDescendantDepth(acc, pred):
  '''
  Internal function for locating one descendant. Called by L{findDescendant} to
  start the search.

  @param acc: Root accessible of the search
  @type acc: Accessibility.Accessible
  @param pred: Search predicate returning True if accessible matches the 
    search criteria or False otherwise
  @type pred: callable
  @return: Matching node or None to keep searching
  @rtype: Accessibility.Accessible or None
  '''
  try:
    if pred(acc): return acc
  except Exception:
    pass
  for child in acc:
    try:
      ret = _findDescendantDepth(child, pred)
    except Exception:
      ret = None
    if ret is not None: return ret
    
def findAllDescendants(acc, pred):
  '''
  Searches for all descendant nodes satisfying the given predicate starting at 
  this node. Does an in-order traversal. For example,
  
  pred = lambda x: x.getRole() == pyatspi.ROLE_PUSH_BUTTON
  buttons = pyatspi.findAllDescendants(node, pred)
  
  will locate all push button descendants of node.
  
  @param acc: Root accessible of the search
  @type acc: Accessibility.Accessible
  @param pred: Search predicate returning True if accessible matches the 
      search criteria or False otherwise
  @type pred: callable
  @return: All nodes matching the search criteria
  @rtype: list
  '''
  matches = []
  _findAllDescendants(acc, pred, matches)
  return matches

def _findAllDescendants(acc, pred, matches):
  '''
  Internal method for collecting all descendants. Reuses the same matches
  list so a new one does not need to be built on each recursive step.
  '''
  for child in acc:
    try:
      if pred(child): matches.append(child)
    except Exception:
      pass
    findAllDescendants(child, pred, matches)
  
def findAncestor(acc, pred):
  '''
  Searches for an ancestor satisfying the given predicate. Note that the
  AT-SPI hierarchy is not always doubly linked. Node A may consider node B its
  child, but B is not guaranteed to have node A as its parent (i.e. its parent
  may be set to None). This means some searches may never make it all the way
  up the hierarchy to the desktop level.
  
  @param acc: Starting accessible object
  @type acc: Accessibility.Accessible
  @param pred: Search predicate returning True if accessible matches the 
    search criteria or False otherwise
  @type pred: callable
  @return: Node matching the criteria or None if not found
  @rtype: Accessibility.Accessible
  '''
  if acc is None:
    # guard against bad start condition
    return None
  while 1:
    if acc.parent is None:
      # stop if there is no parent and we haven't returned yet
      return None
    try:
      if pred(acc.parent): return acc.parent
    except Exception:
      pass
    # move to the parent
    acc = acc.parent

def getPath(acc):
  '''
  Gets the path from the application ancestor to the given accessible in
  terms of its child index at each level.
  
  @param acc: Target accessible
  @type acc: Accessibility.Accessible
  @return: Path to the target
  @rtype: list of integer
  @raise LookupError: When the application accessible cannot be reached
  '''
  path = []
  while 1:
    if acc.parent is None:
      path.reverse()
      return path
    try:
      path.append(acc.getIndexInParent())
    except Exception:
      raise LookupError
    acc = acc.parent

class StateSet(Accessibility__POA.StateSet):
  '''
  Convenience implementation of AT-SPI StateSet, for future use with Collection
  interface.
  
  @param states: Set of states
  @type states: set
  '''
  def __init__(self, *states):
    '''Initializes the state set with the given states.'''
    self.states = set(states)
    
  def contains(self, state):
    '''
    Checks if this L{StateSet} contains the given state.
    
    @param state: State to check
    @type state: Accessibility.StateType
    @return: True if the set contains the given state
    @rtype: boolean
    '''
    return state in self.states
  
  def add(self, *state):
    '''
    Adds one or more states to this set.
    
    @param state: State(s) to add
    @type state: Accessibility.StateType
    '''
    self.states.add(state)
  
  def remove(self, *state):
    '''
    Removes one or more states from this set.
    
    @param state: State(s) to remove
    @type state: Accessibility.StateType
    '''
    self.states.remove(state)
  
  def equals(self, state_set):
    '''
    Checks if this L{StateSet} contains exactly the same members as the given
    L{StateSet}.
    
    @param state_set: Another set
    @type state_set: L{StateSet}
    @return: Are the sets equivalent in terms of their contents?
    @rtype: boolean
    '''
    return self.state_set == self.states
  
  def compare(self, state_set):
    '''
    Computes the symmetric differences of this L{StateSet} and the given
    L{StateSet}.
    
    @param state_set: Another set
    @type state_set: L{StateSet}
    @return: Elements in only one of the two sets
    @rtype: L{StateSet}
    '''
    diff = self.states.symmetric_difference(state_set.states)
    return StateSet(*diff)
  
  def isEmpty(self):
    '''
    Checks if this L{StateSet} is empty.
    
    @return: Is it empty?
    @rtype: boolean
    '''
    return len(self.states) == 0

  def getStates(self):
    '''
    Gets the sequence of all states in this set.
    
    @return: List of states
    @rtype: list
    '''
    return list(self.states)