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

GLADE_FILENAME = os.path.join(sys.prefix, 'share', 'accerciser', 'glade', 
                              'accerciser.glade')
if not os.path.exists(GLADE_FILENAME):
  GLADE_FILENAME = os.path.join(os.getcwd(), 'accerciser.glade')
  
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
    root_atk.set_description(str(os.getpid()))

    # parse the glade
    self.main_xml = gtk.glade.XML(GLADE_FILENAME, 'window', 
                                  gettext.textdomain())
    self.window = self.main_xml.get_widget('window')
    self.window.set_icon_name('accerciser')
    window_size = self.loadSettings('main').get('window_size')
    width, height = window_size or (640, 640)
    self.window.set_default_size(width, height)
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
    self.plugin_manager = PluginManager(self.node, 
                                        [self.plugin_view1, self.plugin_view2])
    self.plugin_manager.loadPlugins()

    # connect signal handlers and show the GUI in its initial state
    self.main_xml.signal_autoconnect(self)
    self.window.show_all()

    self.event_manager = pyLinAcc.Event.Manager()
    self.event_manager.addClient(self._accEventFocusChanged, 'focus')
    self.event_manager.addClient(self._accEventKeyPressed, 'keyboard:press')
    self.last_focused = None

  def _onRefreshAll(self, widget):
    '''
    Refreshes the entire tree at the desktop level.
    '''
    self.acc_treeview.refreshTopLevel()

  def _onRefreshCurrent(self, widget):
    self.acc_treeview.refreshCurrentLevel()

  def _onAccesibleChange(self, node, acc):
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
    self.saveSettings('main', {'window_size' :
                                 (self.window.allocation.width,
                                  self.window.allocation.height)})
    self.event_manager.close()
    self.acc_treeview.destroy()
    self.plugin_manager.close()

  def _onQuit(self, widget):
    '''
    Quits the app.
    '''
    self._shutDown()
    gtk.main_quit()
    
  def _onAbout(self, widget):
    '''
    Shows the about dialog.
    '''
    xml = gtk.glade.XML(GLADE_FILENAME, 'about', gettext.textdomain())
    about = xml.get_widget('about')
    prog = program_get()
    about.set_version(prog.get_app_version())
    xml.signal_autoconnect(self)

  def _onAboutResponse(self, widget, response_id):
    '''
    close the about dialog.
    '''
    if response_id == gtk.RESPONSE_CANCEL:
      widget.destroy()
    
  def _onHelp(self, widget):
    '''
    Shows the help dialog.
    '''
    gnome.help_display('accerciser.xml')
    
  def _onCloseDialog(self, widget):
    '''
    Closes the window of the widget firing this event.
    '''
    widget.get_parent_window().destroy()

  def run(self):
    '''
    Runs the app.
    '''
    try:
      gtk.main()
    except KeyboardInterrupt:
      self._shutDown()

  def _onShowPlugins(self, widget):
     plugins_frame = self.main_xml.get_widget('frame_plugins')
     if widget.get_active():
        plugins_frame.show()
     else:
        plugins_frame.hide()
     
  def _onShowEventMonitor(self, widget):
    self.monitor_window.run()

  def _onSelectToggled(self, widget):
    if widget.get_active():
      self.event_manager.addClient(self._followFocus, 'focus')
    else:
      self.event_manager.removeClient(self._followFocus, 'focus')

  def _accEventFocusChanged(self, event):
    if not self.isMyApp(event.source):
      self.last_focused = event.source

  def _followFocus(self, event):
    if self.isMyApp(event.source):
      return
  
  def _accEventKeyPressed(self, event):
    if (event.any_data[1] & (1 << pyLinAcc.Constants.MODIFIER_META3) and
        event.any_data[0] == '?'):
      # Inspect last focused accessible
      if self.last_focused:
        self.node.update(self.last_focused)
    elif (event.any_data[1] & (1 << pyLinAcc.Constants.MODIFIER_META3) and
          event.any_data[0] == 'A'):
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
          acc, z_order = self._getChildAccAtCoords(frame, x, y)
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
    container = parent
    while container:
      try:
        ci = pyLinAcc.Interfaces.IComponent(container)
      except:
        return None, 0
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
      return acc, z_order
    else:
      return None, 0

  def _onShowPlugins(self, widget):
    xml = gtk.glade.XML(GLADE_FILENAME, 
                        'dialog_plugins', 
                        gettext.textdomain())
    xml.signal_autoconnect(self)
    plugins_treeview = xml.get_widget('plugins_treeview')
    plugins_treeview.set_model(self.plugin_manager.plugins_store)
    crt = gtk.CellRendererText()
    crc = gtk.CellRendererToggle()
    crc.connect('toggled', self._onPluginToggled)
    tvc = gtk.TreeViewColumn('Name')
    tvc.pack_start(crc, True)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=0)
    tvc.set_attributes(crc, active=4)
    plugins_treeview.append_column(tvc)
    crc = gtk.CellRendererCombo()
    tvc = gtk.TreeViewColumn('View')
    tvc.pack_start(crc, False)
    tvc.set_expand(False)
    tvc.set_attributes(crc, text=2)
    crc.set_property('editable', True)
    crc.set_property('model', self.plugin_manager.views_store)
    crc.set_property('text-column', 1)
    crc.set_property('has-entry', True)
    crc.connect('edited', self._onViewChanged)
    plugins_treeview.append_column(tvc)
    d = xml.get_widget('dialog_plugins')
    d.show_all()

  def _onPluginsResponse(self, widget, response):
    widget.destroy()

  def _onPluginToggled(self, renderer_toggle, path):
    self.plugin_manager.togglePlugin(path)

  def _onViewChanged(self, cellrenderertext, path, new_text):
    self.plugin_manager.changeView(path, new_text)

  def _onBottomPanelChange(self, pluginview, page, page_num, action):
    paned = self.main_xml.get_widget('vpaned1')
    if not paned:
      return
    elif pluginview.get_n_pages() == 1 and action == 'added':
      paned.set_position(350)
    elif pluginview.get_n_pages() == 0:
      paned.set_position(paned.allocation.height - 30)

  def _onKeyPress(self, widget, event):
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
