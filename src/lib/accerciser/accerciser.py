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
    self.hotkey_manager.addKeyCombo('Core',_('Core'),
                                    N_('Inspect last focused accessible'),
                                    self._inspectLastFocused, 
                                    gtk.keysyms.a,
                                    gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK)
    self.hotkey_manager.addKeyCombo('Core',_('Core'),
                                    N_('Inspect accessible under mouse'),
                                    self._inspectUnderMouse, 
                                    gtk.keysyms.question,
                                    gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK)

    self.node.connect('accessible_changed', self._onAccesibleChange)

    self.bookmarks_store = BookmarkStore(self.node, self.window.uimanager)

    # load plugins
    self.plugin_manager = \
        PluginManager(self.node, self.hotkey_manager,
                      self.window.pluginview1, self.window.pluginview2)

    # connect signal handlers and show the GUI in its initial state
    self.window.show_all()

    pyatspi.Registry.registerEventListener(self._accEventFocusChanged, 
                                           'focus')

    for action_name, callback in [('Quit', self._onQuit),
                                  ('Preferences', self._onShowPreferences),
                                  ('Contents', self._onHelp),
                                  ('About', self._onAbout)]:
      action = self.window.main_actions.get_action(action_name)
      action.connect('activate', callback)

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
         
  def _accEventFocusChanged(self, event):
    '''
    Hold a reference for the last focused accessible. This is used when a certain 
    global hotkey is pressed to select this accessible.

    @param event: The event that is being handled.
    @type event: L{pyatspi.event.Event}
    '''
    if not self.isMyApp(event.source):
      self.last_focused = event.source

  def _inspectLastFocused(self):
    '''
    Inspect the last focused widget's accessible.
    '''
    if self.last_focused:
      self.node.update(self.last_focused)
      
  def _inspectUnderMouse(self):
    '''
    Inspect accessible of widget under mouse.
    '''
    # Inspect accessible under mouse
    display = gtk.gdk.Display(gtk.gdk.get_display())
    screen, x, y, flags =  display.get_pointer()
    desktop = pyatspi.Registry.getDesktop(0)
    wnck_screen = wnck.screen_get_default()
    window_order = [w.get_name() for w in wnck_screen.get_windows_stacked()]
    top_window = (None, -1)
    for app in desktop:
      if not app or self.isMyApp(app):
        continue
      for frame in app:
        if not frame:
          continue
        acc = self._getChildAccAtCoords(frame, x, y)
        if acc:
          try:
            z_order = window_order.index(frame.name)
          except ValueError:
            continue
          if z_order > top_window[1]:
            top_window = (acc, z_order)
    if top_window[0]:
      self.node.update(top_window[0])

  def _getChildAccAtCoords(self, parent, x, y):
    '''
    Gets any child accessible that resides under given desktop coordinates.

    @param parent: Top-level accessible.
    @type parent: L{Accessibility.Accessible}
    @param x: X coordinate.
    @type x: integer
    @param y: Y coordinate.
    @type y: integer

    @return: Child accessible at given coordinates, or None.
    @rtype: L{Accessibility.Accessible}
    '''
    container = parent
    while True:
      try:
        ci = container.queryComponent()
      except:
        return None
      else:
        inner_container = container
      container =  ci.getAccessibleAtPoint(x, y, pyatspi.DESKTOP_COORDS)
      if not container or container.queryComponent() == ci:
        # The gecko bridge simply has getAccessibleAtPoint return itself
        # if there are no further children
        break
    if inner_container == parent:
      return None
    else:
      return inner_container

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
    
