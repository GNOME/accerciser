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
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import gtk.glade
import gtk.gdk
import os, sys, locale
from icons import getIcon
import os
import atk
import gnome
from bookmarks import BookmarkStore
from accessible_treeview import *
from node import Node
from plugin import PluginManager
from plugin import PluginView
from tools import Tools
from i18n import _, N_
import wnck
from gnome import program_get
import gconf
from hotkey_manager import HotkeyManager, HotkeyTreeView
import gconf
from about_dialog import AccerciserAboutDialog
from prefs_dialog import AccerciserPreferencesDialog
from main_window import AccerciserMainWindow
import ui_manager

GLADE_FILENAME = os.path.join(sys.prefix, 'share', 'accerciser', 'glade', 
                              'accerciser.glade')
if not os.path.exists(GLADE_FILENAME):
  GLADE_FILENAME = os.path.join(os.getcwd(), 'accerciser.glade')
  
GCONF_GENERAL = '/apps/accerciser/general'

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
    self.window.connect('destroy', self._onQuit)

    # Start hotkey manager
    self.hotkey_manager = HotkeyManager()

    self.node.connect('accessible_changed', self._onAccesibleChange)

    self.bookmarks_store = BookmarkStore(self.node)

    # load plugins
    self.plugin_manager = \
        PluginManager(self.node, self.hotkey_manager,
                      self.window.pluginview1, self.window.pluginview2)

    # connect signal handlers and show the GUI in its initial state
    self.window.show_all()

    main_actions = gtk.ActionGroup('MainActions')
    ui_manager.uimanager.insert_action_group(main_actions, 0)
    main_actions.add_actions([
        ('Quit', gtk.STOCK_QUIT, None, 
         '<control>q', 'Quit Accerciser', self._onQuit),
        ('Preferences', gtk.STOCK_PREFERENCES, _('_Preferences...'),
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
                                  gtk.UI_MANAGER_MENUITEM, False)


    self.last_focused = None
    self.window.show_all()

  def run(self):
    '''
    Runs the app.
    '''
    # Tell user if desktop accessibility is disabled.
    self._showNoA11yDialog()
    try:
      pyatspi.Registry.start()
    except KeyboardInterrupt:
      self._shutDown()

  def _showNoA11yDialog(self):
    '''
    Shows a dialog with a relevant message when desktop accessibility seems to
    be disabled. If desktop accessibility is disabled in gconf, prompts the
    user to enable it.
    '''
    cl = gconf.client_get_default()
    if not cl.get_bool('/desktop/gnome/interface/accessibility'):
      message = _('Accerciser could not see the applications on your desktop.'
                  'You must enable desktop accessibility to fix this problem.'
                  'Do you want to enable it now?')
      dialog = gtk.MessageDialog(self.window,type=gtk.MESSAGE_ERROR,
                                 buttons=gtk.BUTTONS_YES_NO, 
                                 message_format=message)
      response_id = dialog.run()
      dialog.destroy()
      if response_id == gtk.RESPONSE_YES:
        cl = gconf.client_get_default()
        cl.set_bool('/desktop/gnome/interface/accessibility', True)
        dialog = gtk.MessageDialog(
          self.window,
          type=gtk.MESSAGE_INFO,
          buttons=gtk.BUTTONS_OK, 
          message_format=_('Note: Changes only take effect after logout.'))
        dialog.run()
        dialog.destroy()

  def _onAccesibleChange(self, node, acc):
    '''
    Callback for "accessible_changed" signal that is emitted by the L{Node}
    referenced as an instance variable.
    Updates the status bar with the path to the selected accessible.

    @param node: The node that emitted the signal.
    @type node: L{Node}
    @param acc: The new accessible that is referenced by the node.
    @type acc: L{Accessibility.Accessible}
    '''
    # Update status bar
    statusbar = self.window.statusbar
    context_id = statusbar.get_context_id('lineage')
    selection = self.window.treeview.get_selection()
    model, iter = selection.get_selected()
    if not iter:
      return
    path = map(str, model.get_path(iter))
    statusbar.pop(context_id)
    if len(path) > 1:
      statusbar.push(context_id, 'Path: '+' '.join(path[1:]))

  def _shutDown(self):
    '''
    Cleans up any object instances that need explicit shutdown.
    '''
    self.window.saveState()
    self.plugin_manager.close()

  def _onQuit(self, obj):
    '''
    Quits the app.

    @param obj: The object that emitted the signal that this callback caught.
    @type obj: L{gtk.Widget}
    '''
    self._shutDown()
    pyatspi.Registry.stop()
    
  def _onAbout(self, action):
    '''
    Shows the about dialog.

    @param widget: The widget that emitted the signal that this callback caught.
    @type widget: L{gtk.Widget}
    '''
    about = AccerciserAboutDialog()
    about.show_all()
    
  def _onHelp(self, action):
    '''
    Shows the help dialog.

    @param widget: The widget that emitted the signal that this callback caught.
    @type widget: L{gtk.Widget}
    '''
    gnome.help_display('accerciser.xml')
         
  def _onShowPreferences(self, action):
    '''
    Shows the preferences dialog.

    @param widget: The widget that emitted the signal that this callback caught.
    @type widget: L{gtk.Widget}
    '''
    plugins_view = self.plugin_manager.View()
    hotkeys_view = HotkeyTreeView(self.hotkey_manager)
    dialog = AccerciserPreferencesDialog(plugins_view, hotkeys_view)
    dialog.show_all()
    
