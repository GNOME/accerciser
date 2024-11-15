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

# test for python modules
modules = ['pygtk', 'gtk', 'Gtk.gdk', 'wnck']
for name in modules:
  try:
    m = __import__(name)
    print(name)
  except ImportError as e:
    if name == 'wnck' and e.args[0].find('gtk') > -1:
      # just no display, continue
      continue
    print(name, '*MISSING*')
    sys.exit(1)
  except RuntimeError:
    # ignore other errors which might be from lack of a display
    continue
  if name == 'pygtk':
    m.require('2.0')
  elif name == 'gtk':
    m.check_version(*GTK_VERSION)

sys.exit(0)
