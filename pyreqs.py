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
PYATSPI_REQ = (2, 23, 3)
GTK_VERSION = (2, 8, 0)

# test for python modules
modules = ['pyatspi', 'cairo', 'rsvg', 'gi', 'gi.repository.Gtk', \
          'gi.repository.GConf', 'gi.repository.Gdk', 'gi.repository.Atk', \
          'gi.repository.GObject', 'gi.repository.GdkPixbuf', \
          'gi.repository.Wnck', 'gi.repository.Gio']

for name in modules:
  try:
    m = __import__(name)
    print(name)
  except ImportError as e:
    print(name, '*MISSING*')
    sys.exit(1)
  except RuntimeError:
    # ignore other errors which might be from lack of a display
    continue
  if name =='pyatspi':
    try:
      compared = [cmp(*x) for x in zip(PYATSPI_REQ, m.__version__)]
    except AttributeError:
      # Installed pyatspi does not support __version__, too old.
      compared = [-1, 0, 0]
    if -1 in compared and 1 not in compared[:compared.index(-1)]:
      # A -1 without a 1 preceding it means an older version.
      print("\nNeed pyatspi 1.23.4 or higher (or SVN trunk)")
      sys.exit(1)
print()
