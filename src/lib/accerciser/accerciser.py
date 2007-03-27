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
import gettext, os, sys, locale
from icons import getIcon
import pyLinAcc
import os
import atk
import gnome
from accessible_treeview import *
from node import Node
from plugin_manager import *
from tools import Tools
from i18n import _
import wnck
from gnome import program_get
import gconf
from hotkey_manager import HotkeyManager, HotkeyTreeView
import gconf

GLADE_FILENAME = os.path.join(sys.prefix, 'share', 'accerciser', 'glade', 
                              'accerciser.glade')
if not os.path.exists(GLADE_FILENAME):
  GLADE_FILENAME = os.path.join(os.getcwd(), 'accerciser.glade')
  
GCONF_GENERAL = '/apps/accerciser/general'

class MainWindow(Tools):
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
    if not root_atk:
      # Gail might have been enabled in gconf, but a logout is still needed.
      self._showNoGailDialog()
      return
    root_atk.set_description(str(os.getpid()))

    # Start hotkey manager
    self.hotkey_manager = HotkeyManager()
    self.hotkey_manager.addKeyCombo('Core', 'Inspect last focused accessible',
                                    self._inspectLastFocused, 
                                    gtk.keysyms.question,
                                    gtk.gdk.SHIFT_MASK | gtk.gdk.MOD1_MASK)
    self.hotkey_manager.addKeyCombo('Core', 'Inspect accessible under mouse',
                                    self._inspectUnderMouse, 
                                    gtk.keysyms.A,
                                    gtk.gdk.SHIFT_MASK | gtk.gdk.MOD1_MASK)

    # parse the glade
    self.main_xml = gtk.glade.XML(GLADE_FILENAME, 'window', 
                                  gettext.textdomain())
    self.window = self.main_xml.get_widget('window')
    self.window.set_icon_name('accerciser')
    cl = gconf.client_get_default()
    width = cl.get_int(GCONF_GENERAL+'/window_width') or 640
    height = cl.get_int(GCONF_GENERAL+'/window_height') or 640
    self.window.set_default_size(width, height)
    for paned_name in ('hpaned', 'vpaned'):
      if not cl.get(GCONF_GENERAL+'/'+paned_name): continue
      paned = self.main_xml.get_widget(paned_name)
      paned_position = cl.get_int(GCONF_GENERAL+'/'+paned_name)
      paned.set_position(paned_position)
      paned.set_data('last_position', paned.get_position())
      
    self.acc_treeview = AccessibleTreeView()
    self.node = self.acc_treeview.node
    self.node.connect('accessible_changed', self._onAccesibleChange)
    scrolled_window = self.main_xml.get_widget('scrolled_acc_tree')
    scrolled_window.add(self.acc_treeview)
    
    bin = self.main_xml.get_widget('alignment_topright')
    self.plugin_view1 = PluginView('Top right')
    bin.add(self.plugin_view1)
    bin = self.main_xml.get_widget('alignment_bottom')
    self.plugin_view2 = PluginView('Bottom panel')
    self.plugin_view2.connect('page_added', 
                              self._onBottomPanelChange, 'added')
    self.plugin_view2.connect('page_removed', 
                              self._onBottomPanelChange, 'removed')
    bin.add(self.plugin_view2)
    # load plugins
    self.plugin_manager = PluginManager(self.node, self.hotkey_manager,
                                        [self.plugin_view1, self.plugin_view2])

    # connect signal handlers and show the GUI in its initial state
    self.main_xml.signal_autoconnect(self)
    self.window.show_all()

    self.event_manager = pyLinAcc.Event.Manager()
    self.event_manager.addClient(self._accEventFocusChanged, 'focus')
    self.event_manager.addClient(self._accEventKeyPressed, 'keyboard:press')
    self.last_focused = None

  def run(self):
    '''
    Runs the app.
    '''
    try:
      gtk.main()
    except KeyboardInterrupt:
      self._shutDown()

  def _showNoGailDialog(self):
    '''
    Shows a dialog with a relevant message when desktop accessibility seems to
    be disabled. If desktop accessibility is disabled in gconf, prompts the
    user to enable it.
    '''
    cl = gconf.client_get_default()
    if not cl.get_bool('/desktop/gnome/interface/accessibility'):
      message = _('Accerciser could not see the applications on your desktop. \
You must enable desktop accessibility to fix this problem. \
Do you want to enable it now?')
      secondary = 'Note: Changes only take effect after logout.'
      buttons = gtk.BUTTONS_YES_NO
    else:
      message = _('Desktop accessibility is still not functioning \
although it has been enabled.')
      secondary = \
          _('Note: You must logout for desktop accessibility options \
to take effect.')
      buttons = gtk.BUTTONS_CLOSE
    dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                               buttons=buttons, 
                               message_format=message)
    dialog.format_secondary_text(secondary)
    
    dialog.connect('response', self._onNoGailResponse)
    dialog.show()

  def _onNoGailResponse(self, dialog, response_id):
    '''
    Callback for the 'response' signal emited from the "no gail" dialog.
    if the response is 'yes', enable accessibility in gconf.

    @param dialog: The dialog that emited the signal.
    @type dialog: L{gtk.MessageDialog}
    @param response_id: Response type that was received.
    @type response_id: integer
    '''
    if response_id == gtk.RESPONSE_YES:
      cl = gconf.client_get_default()
      cl.set_bool('/desktop/gnome/interface/accessibility', True)
    gtk.main_quit()

  def _onRefreshAll(self, widget):
    '''
    Refreshes the entire tree at the desktop level.
    
    @param widget: Widget that emited a signal that this callback 
    caught (if any).
    @type widget: gtk.Widget
    '''
    self.acc_treeview.refreshTopLevel()

  def _onRefreshCurrent(self, widget):
    '''
    Refreshes the currently selected level.
    
    @param widget: Widget that emited a signal that this callback 
    caught.
    @type widget: gtk.Widget
    '''
    self.acc_treeview.refreshCurrentLevel()

  def _onAccesibleChange(self, node, acc):
    '''
    Callback for "accessible_changed" signal that is emitted by the L{Node}
    referenced as an instance variable.
    Updates the status bar with the path to the selected accessible.

    @param node: The node that emitted the signal.
    @type node: L{Node}
    @param acc: The new accessible that is referenced by the node.
    @type acc: L{pyLinAcc.Accessible}
    '''
    # Update status bar
    statusbar = self.main_xml.get_widget('statusbar')
    context_id = statusbar.get_context_id('lineage')
    selection = self.acc_treeview.get_selection()
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
    cl = gconf.client_get_default()
    cl.set_int(GCONF_GENERAL+'/window_width', self.window.allocation.width)
    cl.set_int(GCONF_GENERAL+'/window_height', self.window.allocation.height)
    for paned_name in ('hpaned', 'vpaned'):
      paned = self.main_xml.get_widget(paned_name)
      cl.set_int(GCONF_GENERAL+'/'+paned_name, paned.get_position())    
    self.event_manager.close()
    self.acc_treeview.destroy()
    self.plugin_manager.close()

  def _onQuit(self, widget):
    '''
    Quits the app.

    @param widget: The widget that emitted the signal that this callback caught.
    @type widget: L{gtk.Widget}
    '''
    self._shutDown()
    gtk.main_quit()
    
  def _onAbout(self, widget):
    '''
    Shows the about dialog.

    @param widget: The widget that emitted the signal that this callback caught.
    @type widget: L{gtk.Widget}
    '''
    xml = gtk.glade.XML(GLADE_FILENAME, 'about', gettext.textdomain())
    about = xml.get_widget('about')
    prog = program_get()
    about.set_version(prog.get_app_version())
    xml.signal_autoconnect(self)

  def _onAboutResponse(self, dialog, response_id):
    '''
    Callback for the 'response' signal emited from the "about" dialog.
    Close the dialog if the response is 'cancel'.

    @param dialog: The dialog that emited the signal.
    @type dialog: L{gtk.AboutDialog}
    @param response_id: Response type that was received.
    @type response_id: integer
    '''
    if response_id == gtk.RESPONSE_CANCEL:
      dialog.destroy()
    
  def _onHelp(self, widget):
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
    @type event: L{pyLinAcc.Event}
    '''
    if not self.isMyApp(event.source):
      self.last_focused = event.source

  def _inspectLastFocused(self):
    if self.last_focused:
      self.node.update(self.last_focused)
      
  def _inspectUnderMouse(self):
    # Inspect accessible under mouse
    display = gtk.gdk.Display(gtk.gdk.get_display())
    screen, x, y, flags =  display.get_pointer()
    desktop = pyLinAcc.Registry.getDesktop(0)
    wnck_screen = wnck.screen_get_default()
    window_order = [w.get_name() for w in wnck_screen.get_windows_stacked()]
    top_window = (None, -1)
    for app in desktop:
      if not app:
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

 
  def _accEventKeyPressed(self, event):
    '''
    Handle certain key presses globally. Pass on to the hotkey manager the 
    key combinations pressed for further processing.
    
   @param event: The event that is being handled.
    @type event: L{pyLinAcc.Event}
    '''
    self.hotkey_manager.hotkeyPress(event.any_data[0], event.any_data[1])

  def _getChildAccAtCoords(self, parent, x, y):
    '''
    Gets any child accessible that resides under given desktop coordinates.

    @param parent: Top-level accessible.
    @type parent: L{pyLinAcc.Accessible}
    @param x: X coordinate.
    @type x: integer
    @param y: Y coordinate.
    @type y: integer

    @return: Child accessible at given coordinates, or None.
    @rtype: L{pyLinAcc.Accessible}
    '''
    container = parent
    while container:
      try:
        ci = pyLinAcc.Interfaces.IComponent(container)
      except:
        return None
      container =  ci.getAccessibleAtPoint(
        x, y, pyLinAcc.Constants.DESKTOP_COORDS)
      if container == pyLinAcc.Interfaces.IAccessible(ci):
        # The gecko bridge simply has getAccessibleAtPoint return itself
        # if there are no further children
        container = None
    if ci:
      acc = pyLinAcc.Interfaces.IAccessible(ci)
      if acc == parent:
        acc = None
      ci = pyLinAcc.Interfaces.IComponent(parent)
      z_order = ci.getMDIZOrder()
      return acc
    else:
      return None

  def _onShowPreferences(self, widget):
    '''
    Shows the preferences dialog.

    @param widget: The widget that emitted the signal that this callback caught.
    @type widget: L{gtk.Widget}
    '''
    xml = gtk.glade.XML(GLADE_FILENAME, 
                        'preferences', 
                        gettext.textdomain())
    xml.signal_autoconnect(self)

    sw = xml.get_widget('plugins_sw')
    treeview = PluginTreeView(self.plugin_manager)
    sw.add(treeview)

    sw = xml.get_widget('hotkeys_sw')
    treeview = HotkeyTreeView(self.hotkey_manager)
    sw.add(treeview)

    d = xml.get_widget('preferences')
    d.show_all()
    
  def _onPreferencesResponse(self, dialog, response):
    '''
    Callback for the 'response' signal emited from the "about" dialog.
    Close the dialog if the response is 'cancel'.

    @param dialog: The dialog that emited the signal.
    @type dialog: L{gtk.AboutDialog}
    @param response_id: Response type that was received.
    @type response_id: integer
    '''
    dialog.destroy()

  def _onBottomPanelChange(self, pluginview, page, page_num, action):
    '''
    Callback for changes to the bottom L{PluginView}'s children. If there are no
    tabs, shrink the paned.

    @param pluginview: The L{PluginView} that emitted the signal.
    @type pluginview: L{PluginView}
    @param page: The child widget affected.
    @type page: L{gtk.Widget}
    @param page_num: the new page number for page.
    @type page_num: integer
    @param action: The type of event that accured, either "removed" or "added"
    @type action: string
    '''
    paned = self.main_xml.get_widget('vpaned1')
    if not paned:
      return
    elif pluginview.get_n_pages() == 1 and action == 'added':
      last_pos = paned.get_data('last_position')
      paned.set_position(last_pos or 350)
    elif pluginview.get_n_pages() == 0:
      paned.set_data('last_position', paned.get_position())
      paned.set_position(paned.allocation.height - 30)

  def _onKeyPress(self, widget, event):
    '''
    Callback for a keypress event in the main window.
    Used for navigating plugin tabs (<alt>+num).

    @param widget: The widget that emitted the event.
    @type widget: L{gtk.Widget}
    @param event: The event that accured.
    @type event: L{gtk.gdk.Event}
    '''
    if event.state & gtk.gdk.MOD1_MASK and \
          event.keyval in xrange(gtk.gdk.keyval_from_name('0'), 
                                 gtk.gdk.keyval_from_name('9')):
      tab_num = event.keyval - gtk.gdk.keyval_from_name('0') or 10
      pages_count1 = self.plugin_view1.get_n_pages()
      pages_count2 = self.plugin_view2.get_n_pages()
      if pages_count1 + pages_count2 < tab_num:
        return
      elif pages_count1 >= tab_num:
        self.plugin_view1.set_current_page(tab_num - 1)
      else:
        self.plugin_view2.set_current_page(tab_num - pages_count1 - 1)
