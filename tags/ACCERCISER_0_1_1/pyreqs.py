'''
Checks if all required Python modules are installed.

@author: Peter Parente
@organization: IBM Corporation
@copyright: Copyright (c) 2005, 2007 IBM Corporation
@license: The BSD License

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD License which accompanies
this distribution, and is available at 
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import sys, os

PYGTK_REQ = '2.0'
GTK_VERSION = (2, 8, 0)

try:
  # stop the gail bridge from loading during build
  val = os.environ['GTK_MODULES']
  os.environ['GTK_MODULES'] = val.replace('gail:atk-bridge', '')
except KeyError:
  pass

# test for python modules
modules = ['bonobo', 'ORBit', 'pygtk', 'gtk', 'gtk.glade', 'gtk.gdk', 'wnck']
for name in modules:
  try:
    m = __import__(name)
    print name, 
  except ImportError, e:
    if name == 'wnck' and e.args[0].find('gtk') > -1:
      # just no display, continue
      continue
    print name, '*MISSING*'
    sys.exit(1)
  except RuntimeError:
    # ignore other errors which might be from lack of a display
    continue
  if name == 'pygtk':
    m.require('2.0')
  elif name == 'gtk':
    m.check_version(*GTK_VERSION)

# test for CORBA modules
corba = ['Accessibility']
import bonobo
import ORBit
for name in corba:
  try:
    ORBit.load_typelib(name)
    print name,
  except Exception:
    print name, '*MISSING*'
    sys.exit(1)
sys.exit(0)
