import gtk, gconf
from plugin import PluginView
from i18n import _, N_
from accessible_treeview import *

GCONF_GENERAL = '/apps/accerciser/general'

class AccerciserMainWindow(gtk.Window):
  '''
  Main window class.

  @ivar uimanager: Main window's UImanager.
  @type uimanager: gtk.UIManager
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
    self.main_actions = gtk.ActionGroup('MainActions')
    self.uimanager = gtk.UIManager()
    self.add_accel_group(self.uimanager.get_accel_group())
    # Populate window
    self._populateUI(node)

  def _populateUI(self, node):
    '''
    Populate the top level window widget.
    
    @param node: Main application's node.
    @type node: L{Node}
    '''
    main_vbox = gtk.VBox()
    menu_bar = self._createMenuBar()
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
    self._vpaned.add2(self.pluginview2)
    self._hpaned.add2(self.pluginview1)
    sw = gtk.ScrolledWindow()
    self.treeview = AccessibleTreeView(node)
    self.uimanager.insert_action_group(self.treeview.action_group, 0)
    for action in self.treeview.action_group.list_actions():
      merge_id = self.uimanager.new_merge_id()
      action_name = action.get_name()
      self.uimanager.add_ui(merge_id, '/MainMenuBar/View', 
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


  def _createMenuBar(self):
    '''
    Create actions and menubar UI.
    
    @return: The managed menu bar.
    @rtype: gtk.Menubar()
    '''
    self.main_actions.add_actions([
        ('File', None, _('_File')),
        ('Quit', gtk.STOCK_QUIT, None, 
         '<control>q', 'Quit Accerciser', None),
        ('Edit', None, _('_Edit')),
        ('Preferences', gtk.STOCK_PREFERENCES, _('_Preferences...'),
         '<control>p', 'Show preferences', None),
        ('Bookmarks', None, _('_Bookmarks')),
        ('View', None, _('_View')),
        ('Help', None, _('_Help')),
        ('Contents', gtk.STOCK_HELP, _('_Contents'),
         'F1', 'View contents of manual', None),
        ('About', gtk.STOCK_ABOUT, None,
         None, 'About Accerciser', None)])

    ui = '''
<ui>
  <menubar name="MainMenuBar">
    <menu action="File">
      <menuitem action="Quit"/>
    </menu>
    <menu action="Edit">
      <menuitem action="Preferences"/>
    </menu>
    <menu action="Bookmarks">
    </menu>
    <menu action="View">
    </menu>
    <menu action="Help">
      <menuitem action="Contents"/>
      <menuitem action="About"/>
    </menu>
  </menubar>
</ui>'''

    self.uimanager.insert_action_group(self.main_actions,0)
    self.uimanager.add_ui_from_string(ui)
    
    return self.uimanager.get_widget('/MainMenuBar')

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
    for paned in (self._hpaned, self._vpaned):
      cl.set_int(GCONF_GENERAL+'/'+paned.name, paned.get_position())

  def _onBlinkDone(self, node):
    '''
    Redraw main window after node stops blinking widget. Gets rid of artifacts.
    
    @param node: 
    @type node: 
    '''
    self.queue_draw()
