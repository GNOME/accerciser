'''
Wraps the Gnome Assistive Technology Service Provider Interface for use in
Python. Imports the bonobo and ORBit modules. Initializes the ORBit ORB.
Activates the bonobo Accessibility Registry. Loads the Accessibility typelib
and imports the classes implementing the AT-SPI interfaces.

@var Registry: Reference to the AT-SPI registry daemon intialized on successful
  import
@type Registry: registry.Registry

@author: Peter Parente
@organization: IBM Corporation
@copyright: Copyright (c) 2005, 2007 IBM Corporation
@license: The BSD License

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD license which accompanies
this distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

REGISTRY_IID = "OAFIID:Accessibility_Registry:1.0"
TYPELIB_NAME = "Accessibility"

# import ORBit and bonobo first (required)
import ORBit, bonobo
# initialize the ORB
orb = ORBit.CORBA.ORB_init()
# get a reference to the gnome Accessibility registry
reg = bonobo.activation.activate_from_id(REGISTRY_IID, 0, 0)
if reg is None:
  raise RuntimeError('could not activate:', REGISTRY_IID)
# generate Python code for the Accessibility module from the IDL
ORBit.load_typelib(TYPELIB_NAME)

# import our modules	
import registry, accessible, event, utils
from constants import *

# wrap the raw registry object in our convenience singleton
Registry = registry.Registry(reg)

# throw away extra references
del reg
del orb
