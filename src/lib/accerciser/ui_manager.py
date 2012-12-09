'''
Defines the main UI manager with a layout.

@author: Eitan Isaacson
@organization: Mozilla Foundation
@copyright: Copyright (c) 2007 Mozilla Foundation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import gi

from gi.repository import Gtk as gtk

from .i18n import _, N_, C_

menu_actions = gtk.ActionGroup('MenuActions')

menu_actions.add_actions([
    ('File', None, _('_File')),
    ('Edit', None, _('_Edit')),
    ('Bookmarks', None, C_('menu', '_Bookmarks')),
    ('View', None, C_('menu', '_View')),
    ('Help', None, _('_Help'))])

ui_xml = '''
<ui>
  <menubar name="MainMenuBar">
    <menu action="File">
    </menu>
    <menu action="Edit">
    </menu>
    <menu action="Bookmarks">
    </menu>
    <menu action="View">
      <placeholder name="PluginLayout">
      </placeholder>
      <separator />
      <placeholder name="TreeActions">
      </placeholder>
    </menu>
    <menu action="Help">
    </menu>
  </menubar>
  <popup name="AccTreePopup">
  </popup>
</ui>
'''

MAIN_MENU_PATH = '/MainMenuBar'
FILE_MENU_PATH = MAIN_MENU_PATH+'/File'
EDIT_MENU_PATH = MAIN_MENU_PATH+'/Edit'
BOOKMARKS_MENU_PATH = MAIN_MENU_PATH+'/Bookmarks'
VIEW_MENU_PATH = MAIN_MENU_PATH+'/View'
PLUGIN_LAYOUT_PATH = VIEW_MENU_PATH+'/PluginLayout'
TREE_ACTIONS_PATH = VIEW_MENU_PATH+'/TreeActions'
HELP_MENU_PATH = MAIN_MENU_PATH+'/Help'
POPUP_MENU_PATH = '/AccTreePopup'

uimanager = gtk.UIManager()
uimanager.insert_action_group(menu_actions, 0)
uimanager.add_ui_from_string(ui_xml)
