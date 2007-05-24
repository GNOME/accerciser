'''
Configures the path to pyatspi. Exposes all other package contents.

@author: Eitan Isaacson
@author: Peter Parente
@organization: IBM Corporation
@copyright: Copyright (c) 2006, 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''
import sys, os
# If pyatspi not installed seperately, add pyatspi zip file to the path
try:
  import pyatspi
except ImportError:
  sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'pyatspi.zip'))

def main():
  '''
  Run program.
  '''
  from accerciser import MainWindow
  mw = MainWindow()
  mw.run()
