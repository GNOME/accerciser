'''
Configures the path to pyLinAcc. Exposes all other package contents.

@author: Peter Parente
@organization: IBM Corporation
@copyright: Copyright (c) 2006, 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''
import sys, os
# add pyLinAcc zip file to the path
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'pyLinAcc.zip'))

def main():
  from accerciser import MainWindow
  mw = MainWindow()
  mw.run()