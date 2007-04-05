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
  in the L{pyLinAcc.Constants} module. If such a constant does not exist, the
  string suffix is returned instead. 

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
  the L{Constants} module that has the given value.
  
  @param value: An AT-SPI state
  @type value: Accessibility.StateType
  @return: Human readable, untranslated name of the state
  @rtype: string
  '''
  return constants.STATE_VALUE_TO_NAME.get(value)

def relationToString(value):
  '''
  Converts a relation value to a string based on the name of the state constant
  in the L{Constants} module that has the given value.
  
  @param value: An AT-SPI relation
  @type value: Accessibility.RelationType
  @return: Human readable, untranslated name of the relation
  @rtype: string
  '''
  return constants.RELATION_VALUE_TO_NAME.get(value)

def allModifiers():
  mask = 0
  while mask <= (1 << constants.MODIFIER_NUMLOCK):
    yield mask
    mask += 1
