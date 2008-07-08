import gtk, gconf
from plugin import PluginView
from i18n import _, N_
from accessible_treeview import *
import ui_manager
from ui_manager import uimanager

GCONF_GENERAL = '/apps/accerciser/general'

class AccerciserMainWindow(gtk.Window):
  '''
  Main window class.

  @ivar statusbar: Main window's status bar.
  @type statusbar: gtk.Statusbar
  @ivar treeview: Main accessible tree view.
  @type treeview: L{AccessibleTreeView}
  @ivar pluginview1: Top plugin area.
  @type pluginview1: L{PluginView}
  @ivar pluginview2: Bottom plugin area
  @type pluginview2: L{PluginView}
  @ivar main_actions: Main action group.
  @type main_actions: gtk.ActionGroup
  @ivar _vpaned: Vertical paned.
  @type _vpaned: gtk.VPaned
  @ivar _hpaned: Horizontal paned.
  @type _hpaned: gtk.HPaned
  '''

  def __init__(self, node):
    '''
    Initialize the window.
    
    @param node: Main application's node.
    @type node: L{Node}
    '''
    gtk.Window.__init__(self)
    self.set_icon_name('accerciser')
    self.set_title('accerciser')
    self.connect('key-press-event', self._onKeyPress)
    node.connect('blink-done', self._onBlinkDone)    
    cl = gconf.client_get_default()
    width = cl.get_int(GCONF_GENERAL+'/window_width') or 640
    height = cl.get_int(GCONF_GENERAL+'/window_height') or 640
    self.set_default_size(width, height)
    self.add_accel_group(ui_manager.uimanager.get_accel_group())
    # Populate window
    self._populateUI(node)

    selection = self.treeview.get_selection()
    selection.connect('changed', self._onSelectionChanged)

  def _populateUI(self, node):
    '''
    Populate the top level window widget.
    
    @param node: Main application's node.
    @type node: L{Node}
    '''
    main_vbox = gtk.VBox()
    menu_bar = ui_manager.uimanager.get_widget(ui_manager.MAIN_MENU_PATH)
    main_vbox.pack_start(menu_bar, False)
    self._vpaned = gtk.VPaned()
    self._vpaned.set_position(350)
    self._vpaned.set_name('vpaned')
    main_vbox.pack_start(self._vpaned)
    self.statusbar = gtk.Statusbar()
    main_vbox.pack_start(self.statusbar, False)
    self._hpaned = gtk.HPaned()
    self._hpaned.set_position(250)
    self._hpaned.set_name('hpaned')
    self._vpaned.add1(self._hpaned)
    self.pluginview1 = PluginView(N_('Top panel'))
    self.pluginview2 = PluginView(N_('Bottom panel'))
    self.pluginview2.connect('page_added', 
                              self._onBottomPanelChange, 'added')
    self.pluginview2.connect('page_removed', 
                              self._onBottomPanelChange, 'removed')
    self.pluginview2.connect_after('realize', self._onBottomPanelRealize)
    self._vpaned.add2(self.pluginview2)
    self._hpaned.add2(self.pluginview1)
    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.set_shadow_type(gtk.SHADOW_IN)
    self.treeview = AccessibleTreeView(node)
    ui_manager.uimanager.insert_action_group(self.treeview.action_group, 0)
    for action in self.treeview.action_group.list_actions():
      merge_id = ui_manager.uimanager.new_merge_id()
      action_name = action.get_name()
      ui_manager.uimanager.add_ui(merge_id, ui_manager.TREE_ACTIONS_PATH, 
                                  action_name, action_name, 
                                  gtk.UI_MANAGER_MENUITEM, False)
    
    merge_id = ui_manager.uimanager.new_merge_id()
    action_name = self.treeview.refresh_current_action.get_name()
    ui_manager.uimanager.add_ui(merge_id, ui_manager.POPUP_MENU_PATH,
                                 action_name, action_name,
                                 gtk.UI_MANAGER_MENUITEM, False)

    sw.add(self.treeview)
    self._hpaned.add1(sw)

    cl = gconf.client_get_default()
    for paned in (self._vpaned, self._hpaned):
      if not cl.get(GCONF_GENERAL+'/'+paned.name): continue
      paned_position = cl.get_int(GCONF_GENERAL+'/'+paned.name)
      paned.set_position(paned_position)
      paned.set_data('last_position', paned.get_position())

    self.add(main_vbox)

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
    if pluginview.get_n_pages() == 1 and action == 'added':
      last_pos = self._vpaned.get_data('last_position')
      self._vpaned.set_position(last_pos or 350)
    elif pluginview.get_n_pages() == 0:
      self._vpaned.set_data('last_position', self._vpaned.get_position())
      self._vpaned.set_position(self._vpaned.allocation.height - 30)

  def _onBottomPanelRealize(self, pluginview):
    if pluginview.get_n_pages() == 0:
      self._vpaned.set_position(self._vpaned.allocation.height - 30)

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
      pages_count1 = self.pluginview1.getNVisiblePages()
      pages_count2 = self.pluginview2.getNVisiblePages()
      if pages_count1 + pages_count2 < tab_num:
        return
      elif pages_count1 >= tab_num:
        self.pluginview1.focusTab(tab_num - 1)
      else:
        self.pluginview2.focusTab(tab_num - pages_count1 - 1)

  def saveState(self):
    '''
    Save the dimensions of the main window, and the position of the panes.
    '''
    cl = gconf.client_get_default()
    cl.set_int(GCONF_GENERAL+'/window_width', self.allocation.width)
    cl.set_int(GCONF_GENERAL+'/window_height', self.allocation.height)
    cl.set_int(GCONF_GENERAL+'/hpaned', self._hpaned.get_position())
    if self.pluginview2.get_n_pages():
      position = self._vpaned.get_position()
    else:
      position = self._vpaned.get_data('last_position')
    if position is not None:
      cl.set_int(GCONF_GENERAL+'/vpaned', position)

  def _onBlinkDone(self, node):
    '''
    Redraw main window after node stops blinking widget. Gets rid of artifacts.
    
    @param node: 
    @type node: 
    '''
    self.queue_draw()

  def _onSelectionChanged(self, selection):
    '''
    Callback for selection "changed" of the main treeview selection.
    Updates the status bar with the path to the selected accessible.

    @param selection: The main tree view's selection object.
    @type node: gtk.TreeSelection
    '''
    model, iter = selection.get_selected()
    context_id = self.statusbar.get_context_id('lineage')
    if not iter:
      return
    path = map(str, model.get_path(iter))
    self.statusbar.pop(context_id)
    if len(path) > 1:
      self.statusbar.push(context_id, 'Path: '+' '.join(path[1:]))
