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

from gi.repository import Gio as gio
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
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
from . import menus, window_manager

class Main(gtk.Application, Tools):
  '''
  Class for the main accerciser window.
  '''
  COL_ACC = 4
  COL_FILLED = 2

  def __init__(self, *args, **kwargs):
    gtk.Application.__init__(self, *args, **kwargs,
                             application_id="org.gtk.accerciser")
    self.window = None

  def do_startup(self):
    '''
    gtk.Application callback that gets called when application starts.
    Set up the application.
    '''
    gtk.Application.do_startup(self)

    # mark the root of this window with its PID so we can easily identify it
    # as this app
    root_atk = atk.get_root()
    root_atk.set_description(str(os.getpid()))

    self.node = Node(window_manager.get_window_manager())
    self.set_menubar(menus.main_menu)

  def do_activate(self):
    '''
    gtk.Application callback when application gets launched
    by desktop environment.
    Set up and show the ApplicationWindow.
    Gets references to important widgets, establishes event handlers,
    configures the tree view, and initializes the tree with the contents of the
    desktop.
    '''
    if self.window:
        self.window.present()
        return

    self.window = AccerciserMainWindow(application=self, node=self.node)
    self.window.connect('delete-event', self._onDeleteEvent)
    self.window.connect('destroy', self._onQuit)

    # Start hotkey manager
    self.hotkey_manager = HotkeyManager()
    self.bookmarks_store = BookmarkStore(self.node, self, self.window)

    # load plugins
    self.plugin_manager = \
        PluginManager(self, self.node, self.hotkey_manager,
                      self.window.pluginview1, self.window.pluginview2)

    # connect signal handlers and show the GUI in its initial state
    self.window.show_all()

    menu_items = [
        (menus.file_menu, 'quit', 'application-exit', _('_Quit'),
         '<control>q', self._onQuit),
        (menus.edit_menu, 'preferences', 'preferences-system', _('_Preferences…'),
         '<control>p', self._onShowPreferences),
        (menus.help_menu, 'contents', 'help-browser', _('_Contents'),
         'F1', self._onHelp),
        (menus.help_menu, 'about', 'help-about', _('_About'),
         None, self._onAbout)]

    self.addMenuItems(menu_items)

    self.last_focused = None
    self.window.show_all()

    try:
      # async is a reserved keyword in Python 3.7+, so we pass the args as dict
      pyatspi.Registry.start(**{'async': True, 'gil': False})
    except KeyboardInterrupt:
      self._shutDown()

  def addMenuItem(self, menu, name, icon_name, label, accel, callback):
    '''
    Create menu item in the given menu and return the menu item and its action.

    @param menu: The menu into which the item should be inserted.
    @type menu: gio.Menu
    @param name: Name for the action
    @type name: string
    @param icon_name: Name of the icon to use.
    @type icon_name: string
    @param label: Label for the menu entry.
    @type label: string
    @param accel: Keyboard accelerator for the action, or None.
    @type accel: string
    @param callback: Callback that gets called when the action gets triggered.
    @type callback: method

    @return: Menu item and action.
    @rtype: tuple(gio.MenuItem, gio.SimpleAction)
    '''
    action_name = 'app.' + name
    menu_item = gio.MenuItem.new(label, action_name)
    icon = gio.ThemedIcon.new(icon_name)
    menu_item.set_icon(icon)
    menu.append_item(menu_item)
    action = gio.SimpleAction.new(name, None)
    action.connect('activate', callback)
    if accel:
      self.set_accels_for_action(action_name, [accel])
    self.add_action(action)
    return menu_item, action

  def addMenuItems(self, menu_items):
    '''
    Add menu items. The parameter is a list of tuples containing
    all parameters that L{addMenuItem} takes.
    See L{addMenuItem} for more details.

    @param menu_items
    @type list(tuple(gio.Menu, string, string, string, string, method))
    '''
    for menu, name, icon_name, label, accel, callback in menu_items:
      self.addMenuItem(menu, name, icon_name, label, accel, callback)

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
    self.quit()

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
    gtk.show_uri_on_window(self.window,
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
