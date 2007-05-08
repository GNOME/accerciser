'''
IPython console plugin.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

from accerciser.plugin import ViewportPlugin
from accerciser.i18n import N_, _
import os
import pyatspi
import gtk
import ipython_view

if ipython_view.IPython == None:
  raise RuntimeError('The IPython module is required for the IPython console')
 

class Console(ViewportPlugin):
  plugin_name = N_('IPython Console')
  plugin_name_localized = _(plugin_name)
  plugin_description = \
      N_('Interactive console for manipulating currently selected accessible')
  def init(self):
    sw = gtk.ScrolledWindow()
    self.plugin_area.add(sw)
    self.ipython_view = ipython_view.IPythonView()
    self.ipython_view.updateNamespace({'acc': None})
    self.ipython_view.updateNamespace(pyatspi.__dict__)
    self.ipython_view.updateNamespace({'desktop': 
                                      pyatspi.Registry.getDesktop(0)})
    self.ipython_view.updateNamespace({'show': self._showAcc})
    sw.add(self.ipython_view)
  
  def onAccChanged(self, acc):
    self.ipython_view.updateNamespace({'acc': acc})

  def _showAcc(self, acc):
    self.node.update(acc)
