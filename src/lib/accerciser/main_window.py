from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository.Gio import Settings as GSettings

from .plugin import PluginView
from .i18n import _, N_
from .accessible_treeview import *

GSCHEMA = 'org.a11y.Accerciser'

class AccerciserMainWindow(gtk.ApplicationWindow):
  '''
  Main window class.

  @ivar application: Main application.
  @type application: gtk.Application
  @ivar statusbar: Main window's status bar.
  @type statusbar: gtk.Statusbar
  @ivar treeview: Main accessible tree view.
  @type treeview: L{AccessibleTreeView}
  @ivar pluginview1: Top plugin area.
  @type pluginview1: L{PluginView}
  @ivar pluginview2: Bottom plugin area
  @type pluginview2: L{PluginView}
  @ivar _vpaned: Vertical paned.
  @type _vpaned: gtk.Paned
  @ivar _hpaned: Horizontal paned.
  @type _hpaned: gtk.Paned
  '''
  __gtype_name__ = "AccerciserMainWindow"

  def __init__(self, *args, application=None, node=None, **kwargs):
    '''
    Initialize the window.

    @param application: Main application.
    @type application: gtk.Application
    @param node: Main application's node.
    @type node: L{Node}
    '''
    gtk.ApplicationWindow.__init__(self, *args, application=application, **kwargs)
    self.application = application
    self.set_icon_name('accerciser')
    self.set_title(_('Accerciser Accessibility Explorer'))
    self.connect('key-press-event', self._onKeyPress)
    self.gsettings = GSettings.new(GSCHEMA)
    width = self.gsettings.get_int('window-width') or 640
    height = self.gsettings.get_int('window-height') or 640
    self.set_default_size(width, height)
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
    main_vbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)
    self._vpaned = gtk.Paned(orientation=gtk.Orientation.VERTICAL)
    self._vpaned.set_position(350)
    self._vpaned.set_name('vpaned')
    main_vbox.pack_start(self._vpaned, True, True, 0)
    self.statusbar = gtk.Statusbar()
    main_vbox.pack_start(self.statusbar, False, True, 0)
    self._hpaned = gtk.Paned(orientation=gtk.Orientation.HORIZONTAL)
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
    sw.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
    sw.set_shadow_type(gtk.ShadowType.IN)
    self.treeview = AccessibleTreeView(self.application, node)

    sw.add(self.treeview)
    self._hpaned.add1(sw)

    for paned in (self._vpaned, self._hpaned):
      if not self.gsettings.get_int(paned.get_name()): continue
      paned_position = self.gsettings.get_int(paned.get_name())
      paned.set_position(paned_position)
      setattr(paned, 'last_position', paned.get_position())

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
      last_pos = getattr(self._vpaned, 'last_position')
      self._vpaned.set_position(last_pos or 350)
    elif pluginview.get_n_pages() == 0:
      setattr(self._vpaned, 'last_position', self._vpaned.get_position())
      self._vpaned.set_position(self._vpaned.get_allocated_height() - 30)

  def _onBottomPanelRealize(self, pluginview):
    if pluginview.get_n_pages() == 0:
      self._vpaned.set_position(self._vpaned.get_allocated_height() - 30)

  def _onKeyPress(self, widget, event):
    '''
    Callback for a keypress event in the main window.
    Used for navigating plugin tabs (<alt>+num).

    @param widget: The widget that emitted the event.
    @type widget: L{gtk.Widget}
    @param event: The event that accured.
    @type event: L{gtk.gdk.Event}
    '''
    if event.state & gdk.ModifierType.MOD1_MASK and \
          event.keyval in range(gdk.keyval_from_name('0'),
                                 gdk.keyval_from_name('9')):
      tab_num = event.keyval - gdk.keyval_from_name('0') or 10
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
    self.gsettings.set_int('window-width', self.get_allocated_width())
    self.gsettings.set_int('window-height', self.get_allocated_height())
    self.gsettings.set_int('hpaned', self._hpaned.get_position())
    if self.pluginview2.get_n_pages():
      position = self._vpaned.get_position()
    else:
      position = getattr(self._vpaned, 'last_position')
    if position is not None:
      self.gsettings.set_int('vpaned', position)

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
    tree_path = model.get_path(iter)
    path_tuple = tuple(tree_path.get_indices())

    path = list(map(str, path_tuple))
    self.statusbar.pop(context_id)
    if len(path) > 1:
      self.statusbar.push(context_id, 'Path: '+' '.join(path[1:]))
