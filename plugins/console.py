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

import gi

from gi.repository import Gtk as gtk

from accerciser.plugin import ViewportPlugin
from accerciser.i18n import N_, _
import os
import pyatspi
import ipython_view

if ipython_view.IPython == None:
  raise RuntimeError('The IPython module is required for the IPython console')


class Console(ViewportPlugin):
  '''
  Plugin class for IPython console.
  '''
  plugin_name = N_('IPython Console')
  plugin_name_localized = _(plugin_name)
  plugin_description = \
      N_('Interactive console for manipulating currently selected accessible')
  def init(self):
    '''
    Initialize plugin.
    '''
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
    '''
    Update 'acc' variable in console namespace with currently
    selected accessible.

    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    self.ipython_view.updateNamespace({'acc': acc})

  def _showAcc(self, acc):
    '''
    A method that is exposed in the console's namespace that allows the user
    to show a given accessible in the main application.

    @param acc: Accessible to show.
    @type acc: Accessibility.Accessible
    '''
    self.node.update(acc)
