'''
Defines the main program classes for creating the GUI, drawing the blinking
selection rectangle, and maintaining information about the currently selected
accessible.

@author: Peter Parente
@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2006, 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import Wnck as wnck
from gi.repository import GLib
from gi.repository import Atk as atk

import os, sys, locale
from .icons import getIcon
import os
from .bookmarks import BookmarkStore
from .accessible_treeview import *
from .node import Node
from .plugin import PluginManager
from .plugin import PluginView
from .tools import Tools
from .i18n import _, N_
from .hotkey_manager import HotkeyManager, HotkeyTreeView
from .about_dialog import AccerciserAboutDialog
from .prefs_dialog import AccerciserPreferencesDialog
from .main_window import AccerciserMainWindow
from . import ui_manager

class Main(Tools):
  '''
  Class for the main accerciser window. 
  '''
  COL_ACC = 4
  COL_FILLED = 2
  
  def __init__(self):
    '''
    Gets references to important widgets, establishes event handlers,
    configures the tree view, and initializes the tree with the contents of the
    desktop.
    '''
    # mark the root of this window with its PID so we can easily identify it
    # as this app
    root_atk = atk.get_root()
    root_atk.set_description(str(os.getpid()))

    self.node = Node()

    self.window = AccerciserMainWindow(self.node)
    self.window.connect('delete-event', self._onDeleteEvent)
    self.window.connect('destroy', self._onQuit)

    # Start hotkey manager
    self.hotkey_manager = HotkeyManager()
    self.bookmarks_store = BookmarkStore(self.node, self.window)

    # load plugins
    self.plugin_manager = \
        PluginManager(self.node, self.hotkey_manager,
                      self.window.pluginview1, self.window.pluginview2)

    # connect signal handlers and show the GUI in its initial state
    self.window.show_all()

    main_actions = gtk.ActionGroup.new('MainActions')
    ui_manager.uimanager.insert_action_group(main_actions, 0)
    main_actions.add_actions([
        ('Quit', gtk.STOCK_QUIT, None, 
         '<control>q', 'Quit Accerciser', self._onQuit),
        ('Preferences', gtk.STOCK_PREFERENCES, _('_Preferences…'),
         '<control>p', 'Show preferences', self._onShowPreferences),
        ('Contents', gtk.STOCK_HELP, _('_Contents'),
         'F1', 'View contents of manual', self._onHelp),
        ('About', gtk.STOCK_ABOUT, None,
         None, 'About Accerciser', self._onAbout)])

    for action_name, menu_path in [('Quit', ui_manager.FILE_MENU_PATH),
                                  ('Preferences', ui_manager.EDIT_MENU_PATH),
                                  ('Contents', ui_manager.HELP_MENU_PATH),
                                  ('About', ui_manager.HELP_MENU_PATH)]:
      action = main_actions.get_action(action_name)
      ui_manager.uimanager.add_ui(ui_manager.uimanager.new_merge_id(), 
                                  menu_path, action_name, action_name, 
                                  gtk.UIManagerItemType.MENUITEM, False)


    self.last_focused = None
    self.window.show_all()

  def run(self):
    '''
    Runs the app.
    '''
    GLib.timeout_add(200, self._pumpEvents)
    try:
      # async is a reserved keyword in Python 3.7+, so we pass the args as dict
      pyatspi.Registry.start(**{'async': True, 'gil': False})
    except KeyboardInterrupt:
      self._shutDown()

  def _pumpEvents(self):
    pyatspi.Registry.pumpQueuedEvents()
    return True

  def _shutDown(self):
    '''
    Cleans up any object instances that need explicit shutdown.
    '''
    self.plugin_manager.close()

  def _onQuit(self, obj, data=None):
    '''
    Quits the app.

    @param obj: The object that emitted the signal that this callback caught.
    @type obj: L{gtk.Widget}
    '''
    self._shutDown()
    pyatspi.Registry.stop()
    
  def _onAbout(self, action, data=None):
    '''
    Shows the about dialog.

    @param widget: The widget that emitted the signal that this callback caught.
    @type widget: L{gtk.Widget}
    '''
    about = AccerciserAboutDialog()
    about.set_transient_for(self.window)
    about.run()
    
  def _onHelp(self, action, page=""):
    '''
    Shows the help dialog.

    @param widget: The widget that emitted the signal that this callback caught.
    @type widget: L{gtk.Widget}
    '''
    uri = "help:accerciser"
    if page:
        uri += "/%s" % page
    gtk.show_uri(gdk.Screen.get_default(),
                 uri,
                 gtk.get_current_event_time())
    return True
         
  def _onShowPreferences(self, action, data=None):
    '''
    Shows the preferences dialog.

    @param widget: The widget that emitted the signal that this callback caught.
    @type widget: L{gtk.Widget}
    '''
    plugins_view = self.plugin_manager.View()
    hotkeys_view = HotkeyTreeView(self.hotkey_manager)
    dialog = AccerciserPreferencesDialog(plugins_view, hotkeys_view)
    dialog.set_transient_for(self.window)
    dialog.show_all()

  def _onDeleteEvent(self, obj, data=None):
    '''
    Handles when a delete-event is triggered from the main window.

    @param obj: The object that emitted the signal that this callback caught.
    @type obj: L{gtk.Widget}
    '''
    self.window.saveState()
