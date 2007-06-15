'''
Defines the preferences dialog.

@author: Eitan Isaacson
@organization: Mozilla Foundation
@copyright: Copyright (c) 2006, 2007 Mozilla Foundation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import gtk
from i18n import _

class AccerciserPreferencesDialog(gtk.Dialog):
  '''
  Class that creates a preferences dialog.
  '''
  def __init__(self, plugins_view=None, hotkeys_view=None):
    '''
    Initialize a preferences dialog.
    
    @param plugins_view: Treeview of plugins.
    @type plugins_view: L{PluginManager._View}
    @param hotkeys_view: Treeview of global hotkeys.
    @type hotkeys_view: L{HotkeyTreeView}
    '''
    gtk.Dialog.__init__(self, _('accerciser Preferences'), 
                        buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
    self.connect('response', self._onResponse)
    self.set_default_size(500,250)
    notebook = gtk.Notebook()
    self.vbox.add(notebook)
    for view, section in [(plugins_view, _('Plugins')),
                          (hotkeys_view, _('Global Hotkeys'))]:
      if view is not None:
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        notebook.append_page(sw, gtk.Label(section))
        
  def _onResponse(self, dialog, response_id):
    '''
    Callback for dialog responses, always destroy it.
    
    @param dialog: This dialog.
    @type dialog: L{AccerciserPreferencesDialog}
    @param response_id: Response ID recieved.
    @type response_id: integer
    '''
    self.destroy()
