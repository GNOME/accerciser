'''
Defines the manager for plugin layout and loading.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2006, 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''
import gtk
import gobject
from plugin import PluginErrorMessage, Plugin
from tools import Tools, GConfListWrapper
import os
import sys
import imp
import pango
import traceback
import gconf
from i18n import _, N_

GCONF_PLUGIN_DISABLED = '/apps/accerciser/disabled_plugins'
GCONF_PLUGINVIEWS = '/apps/accerciser/pluginviews'

PLUGIN_NOTEBOOK_GROUP = 1

class PluginView(gtk.Notebook):
  __gsignals__ = {'new_view' : 
                  (gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, 
                   (gobject.TYPE_OBJECT,))}
  TARGET_PLUGINVIEW = 0
  TARGET_ROOTWIN = 1

  def __init__(self, view_name):
    gtk.Notebook.__init__(self)
    self.view_name = view_name
    self.set_scrollable(True)
    self.set_group_id(PLUGIN_NOTEBOOK_GROUP)
    self.connect('drag_end', self._onDragEnd)
    self.connect('drag_data_get', self._onDragDataGet)
    self.dest_type = None
    
  def _onDragDataGet(self, widget, context, selection_data, info, time):
    self.dest_type = info
    selection_data.set(selection_data.target, 8, '')

  def _onDragEnd(self, widget, drag_context):
    if self.dest_type == self.TARGET_PLUGINVIEW:
      return
    index = self.get_current_page()
    child = self.get_nth_page(index)
    self.emit('new_view', child)

  def insert_page(self, child, tab_label=None, position=-1):
    if tab_label:
      name = tab_label
    elif isinstance(child, Plugin):
      name = getattr(child,'plugin_name_localized', None) or child.plugin_name
    elif child.name:
      name = child.name
    gtk.Notebook.insert_page(self, child, gtk.Label(name), position=position)
    self.set_tab_detachable(child, True)
    self.set_tab_reorderable(child, True)

  def append_page(self, child, tab_label=None):
    self.insert_page(child, tab_label, -1)

  def prepend_page(self, child, tab_label=None):
    self.insert_page(child, tab_label, 0)

  def focusTab(self, tab_num):
    self.set_current_page(tab_num)
    self.grab_focus()

class PluginViewWindow(gtk.Window, Tools):
  def __init__(self, view_name):
    gtk.Window.__init__(self)
    self.plugin_view = PluginView(view_name)
    self.add(self.plugin_view)

    cl = gconf.client_get_default()
    escaped_view_name = '/%s' % gconf.escape_key(view_name, len(view_name))
    width = cl.get_int(GCONF_PLUGINVIEWS+escaped_view_name+'/width') or 480
    height = cl.get_int(GCONF_PLUGINVIEWS+escaped_view_name+'/height') or 480
    self.set_default_size(width, height)
    self.connect('key_press_event', self._onKeyPress)
    self.plugin_view.connect('page_removed', self._onPluginRemoved)
    self.set_title(view_name)
    self.set_position(gtk.WIN_POS_MOUSE)
    self.show_all()
    self.connect('size-allocate', self._onResize)

  def _onResize(self, widget, allocation):
    view_name = self.plugin_view.view_name
    key_prefix = '%s/%s' % \
        (GCONF_PLUGINVIEWS, 
         gconf.escape_key(view_name, len(view_name)))
    cl = gconf.client_get_default()
    cl.set_int(key_prefix+'/width', self.allocation.width)
    cl.set_int(key_prefix+'/height', self.allocation.height)

  def _onPluginRemoved(self, pluginview, page, page_num):
    if pluginview.get_n_pages() == 0:
      self.destroy()

  def _onKeyPress(self, widget, event):
    if event.state & gtk.gdk.MOD1_MASK and \
          event.keyval in xrange(gtk.gdk.keyval_from_name('0'), 
                                 gtk.gdk.keyval_from_name('9')):
      tab_num = event.keyval - gtk.gdk.keyval_from_name('0') or 10
      pages_count = self.plugin_view.get_n_pages()
      if pages_count >= tab_num:
        self.plugin_view.focusTab(tab_num - 1)
      

class PluginManager(gtk.ListStore, Tools):
  def __init__(self, node, hotkey_manager, pluginviews_main):
    gtk.ListStore.__init__(self,
                           str, # Plugin name
                           str, # Plugin description
                           object, # View
                           object, # Plugin instance
                           str, # Plugin class name
                           str, # Plugin file name
                           str, # Plugin path
                           str) # Plugin translated name
    for i, col in enumerate(['NAME', 'DESC', 'VIEW', 'INSTANCE', 
                             'CLASS', 'FILE', 'PATH', 'LOCALIZED']):
      setattr(self, 'COL_'+col, i)
    self.node = node
    self.gconf_client = gconf.client_get_default()
    self.hotkey_manager = hotkey_manager
    self.pluginviews_main = pluginviews_main
    for main_view in pluginviews_main:
      self.append(['', '', main_view, 
                   None, '', '', '',''])
    self.views_store = self.filter_new()
    self.views_store.set_visible_func(self._viewStoreVisible)
    self.views_store.set_modify_func([object, str], self._viewsStoreModify)
    self.VIEWSTORE_VIEW = 0
    self.VIEWSTORE_NAME = 1
    self.plugins_store = self.filter_new()
    self.plugins_store.set_visible_func(self._pluginStoreVisible)
    self.error_manager = PluginErrorManager(self.pluginviews_main[-1])
    self._loadPlugins()
    self.connect('row-changed', self._onPluginRowChanged)

  def close(self):
    for row in self:
      plugin = row[self.COL_INSTANCE]
      if plugin:
        plugin._close()

  def _loadPlugins(self):
    for plugin_dir, plugin_fn in self._getPluginFiles():
      self._loadPluginFile(plugin_dir, plugin_fn)
    for view in self._getViewInstances():
      self._reorderPluginView(view)
      self._connectSignals(view)
      view.set_current_page(0)
      view.show_all()
    self.error_manager.keepOnTop()

  def _getPluginFiles(self):
    plugin_file_list = []
    plugin_dir_local = os.path.join(os.environ['HOME'], 
                                    '.accerciser', 'plugins')
    plugin_dir_global = os.path.join(sys.prefix, 'share',
                                     'accerciser', 'plugins')
    for plugin_dir in (plugin_dir_local, plugin_dir_global):
      if not os.path.isdir(plugin_dir):
        continue
      for fn in os.listdir(plugin_dir):
        if fn.endswith('.py') and not fn.startswith('.'):
          plugin_file_list.append((plugin_dir, fn[:-3]))

    return plugin_file_list

  def _reorderPluginView(self, view):
    plugin_layouts = PluginMapping()
    try:
      plugin_layout = plugin_layouts[view.view_name]
    except KeyError:
      plugin_layouts[view.view_name] = []
      plugin_layout = plugin_layouts[view.view_name]
    plugin_dict = {}
    for child in view.get_children():
      if isinstance(child, Plugin):
        plugin_dict[child.plugin_name] = child
    for plugin_name in reversed(plugin_layout):
      if plugin_dict.has_key(plugin_name):
        view.reorder_child(plugin_dict[plugin_name], 0)

  def _getPluginLocals(self, plugin_dir, plugin_fn):
    sys.path.insert(0, plugin_dir)
    try:
      params = imp.find_module(plugin_fn, [plugin_dir])
      plugin = imp.load_module(plugin_fn, *params)
      plugin_locals = plugin.__dict__
    except Exception, e:
      error_message = self.error_manager.newError(
        traceback.format_exception_only(e.__class__, e)[0].strip(),
        traceback.format_exc())
      error_message.connect('response', self._onRetryFileLoad, (plugin_dir, plugin_fn))
      return {}
    sys.path.pop(0)
    return plugin_locals

  def _onRetryFileLoad(self, error_message, response_id, plugin_file_info):
    if response_id == gtk.RESPONSE_APPLY:
      self._loadPluginFile(plugin_file_info[0], 
                           plugin_file_info[1])
      error_message.emit('response', gtk.RESPONSE_CLOSE)

  def _loadPluginFile(self, plugin_dir, plugin_fn):
    plugin_locals = self._getPluginLocals(plugin_dir, plugin_fn)
    # use keys list to avoid size changes during iteration
    for symbol in plugin_locals.keys():
      try:
        is_plugin = \
            issubclass(plugin_locals[symbol], Plugin) and \
            hasattr(plugin_locals[symbol], 'plugin_name')
      except TypeError:
        continue
      if is_plugin:
        view_name = self._getViewNameForPlugin(plugin_locals[symbol].plugin_name)
        try:
          iter = self.append([plugin_locals[symbol].plugin_name,
                              plugin_locals[symbol].plugin_description,
                              self._getViewByName(view_name),
                              None, symbol, plugin_fn, plugin_dir,
                              getattr(plugin_locals[symbol], 
                                      'plugin_name_localized', None)])
        except AttributeError, e:
          error_message = self.error_manager.newError(
            traceback.format_exception_only(e.__class__, e)[0].strip(),
            traceback.format_exc())
          error_message.connect('response', self._onRetryFileLoad, 
                                (plugin_dir, plugin_fn))
          continue
        # if a plugin class is found, initialize
        enabled = plugin_locals[symbol].plugin_name not in \
            GConfListWrapper(GCONF_PLUGIN_DISABLED)
        if enabled:
          self._enablePlugin(plugin_locals, iter)

  def _enablePlugin(self, plugin_locals, iter, set_current=False):
    plugin_class = plugin_locals.get(self[iter][self.COL_CLASS])
    try:
      plugin_instance = plugin_class(self.node)
      plugin_instance.init()
      plugin_instance.onAccChanged(plugin_instance.node.acc)
      for key_combo in plugin_instance.global_hotkeys:
        self.hotkey_manager.addKeyCombo(
          self[iter][self.COL_NAME], 
          self[iter][self.COL_LOCALIZED], *key_combo)
    except Exception, e:
      error_message = self.error_manager.newError(
        traceback.format_exception_only(e.__class__, e)[0].strip(),
        traceback.format_exc())
      error_message.connect('response', self._onRetryPluginEnable, iter)
      return
    self[iter][self.COL_INSTANCE] = plugin_instance
    if isinstance(plugin_instance, gtk.Widget):
      pluginview = self[iter][self.COL_VIEW]
      plugin_instance.connect('reload-request', self._onReloadRequest)
      self._addPluginToView(pluginview, plugin_instance)
      if set_current:
        pluginview.set_current_page(-1)

  def _disablePlugin(self, iter):
    plugin_instance = self[iter][self.COL_INSTANCE]
    if not plugin_instance: return
    for key_combo in plugin_instance.global_hotkeys:
      self.hotkey_manager.removeKeyCombo(
        self[iter][self.COL_NAME], *key_combo)
    if isinstance(plugin_instance, gtk.Widget):
      plugin_instance.destroy()
    plugin_instance._close()
    self[iter][self.COL_INSTANCE] = None

  def _reloadPlugin(self, iter):
    plugin_fn = self[iter][self.COL_FILE]
    plugin_dir = self[iter][self.COL_PATH]
    plugin_locals = self._getPluginLocals(plugin_dir, plugin_fn)
    self._enablePlugin(plugin_locals, iter, True)
    return self[iter][self.COL_INSTANCE]

  def _onRetryPluginEnable(self, error_message, response_id, iter):
    if response_id == gtk.RESPONSE_APPLY:
      self._reloadPlugin(iter)
      error_message.emit('response', gtk.RESPONSE_CLOSE)

  def _onReloadRequest(self, plugin):
    iter = None
    for row in self:
      if row[self.COL_INSTANCE] == plugin:
        iter = row.iter
        break
    if not iter:
      return
    notebook = plugin.parent
    tab_index = notebook.page_num(plugin)
    self._disablePlugin(iter)
    plugin_instance = self._reloadPlugin(iter)
    if not plugin_instance:
      return
    notebook.reorder_child(plugin_instance, tab_index)

  def togglePlugin(self, path):
    filter_iter = self.plugins_store.get_iter(path)
    iter = self.plugins_store.convert_iter_to_child_iter(filter_iter)
    if self[iter][self.COL_INSTANCE]:
      # Disable plugin
      self._disablePlugin(iter)
    else:
      # Enable plugin
      self._reloadPlugin(iter)

  def _getViewNameForPlugin(self, plugin_name):
    plugin_layouts = PluginMapping()
    for view_name in plugin_layouts:
      if plugin_name in plugin_layouts[view_name]:
        return view_name
    return self.pluginviews_main[0].view_name

  def _getViewByName(self, view_name):
    views_dict = self._getViewNameInstanceDict()
    try:
      view = views_dict[view_name]
    except KeyError:
      w = PluginViewWindow(view_name)
      w.connect('delete_event', self._onPluginViewRemoved)
      view =  w.plugin_view
    return view

  def _addPluginToView(self, view, plugin):
    view.append_page(plugin)
    plugin.show_all()
    
  def _onNewPluginView(self, view, child):
    view.remove(child)
    self._newViewWithPage(child)

  def _newViewWithPage(self, page, view_name=None):
    if not view_name:
      view_name = _('Plugin View')
      view_num = 2
      while view_name in self._getViewNames():
        view_name = _('Plugin View (%d)') % view_num
        view_num += 1
    pluginview = self._getViewByName(view_name)
    self._connectSignals(pluginview)
    pluginview.append_page(page)

  def _onPluginViewRemoved(self, pluginviewwindow, event):
    pluginview = pluginviewwindow.plugin_view
    for child in pluginview.get_children():
      pluginview.remove(child)
      self.pluginviews_main[0].append_page(child)

  def _getIterFromPlugin(self, plugin):
    for row in self:
      if row[self.COL_INSTANCE] == plugin:
        return row.iter
    return None
  
  def _onAddedPluginToView(self, pluginview, page, page_num):
    iter = self._getIterFromPlugin(page)
    if not iter: return
    self[iter][self.COL_VIEW] = pluginview

  def _onReorderedPluginInView(self, pluginview, page, page_num):
    self._saveTabOrder(pluginview)

  def changeView(self, plugin, new_text):
    if not plugin: return
    old_view = plugin.parent
    views_dict = self._getViewNameInstanceDict()
    view = views_dict.get(new_text)
    if view:
      if plugin in view.get_children():
        return
      else:
        old_view.remove(plugin)
        view.append_page(plugin)
    else:
      old_view.remove(plugin)
      self._newViewWithPage(plugin, new_text)

  def _viewStoreVisible(self, model, iter):
    index = model.get_path(iter)[0]
    view = model[iter][self.COL_VIEW]
    views = [row[self.COL_VIEW] for row in model]
    return views.index(view) == index

  def _pluginStoreVisible(self, model, iter):
    return bool(model[iter][self.COL_NAME])

  def _connectSignals(self, pluginview):
    pluginview.connect('new_view', self._onNewPluginView)
    pluginview.connect('page_added', self._onAddedPluginToView)
    pluginview.connect('page_reordered', self._onReorderedPluginInView)

  def _saveTabOrder(self, view):
    plugin_layout = []
    for child in view.get_children():
      if not isinstance(child, Plugin): continue
      plugin_layout.append(child.plugin_name)
    plugin_layouts = PluginMapping()
    plugin_layouts[view.view_name] = plugin_layout

  def _onPluginRowChanged(self, model, path, iter):
    if not model[iter][self.COL_VIEW]: return
    plugin_name = model[iter][self.COL_NAME]
    state = bool(model[iter][self.COL_INSTANCE])
    view_name = model[iter][self.COL_VIEW].view_name
    plugin_layouts = PluginMapping()
    for view_n in plugin_layouts:
      if plugin_name in plugin_layouts[view_n]:
        plugin_layouts[view_n].remove(plugin_name)    
    disabled_list = GConfListWrapper(GCONF_PLUGIN_DISABLED)
    if not state:
      if plugin_name not in disabled_list:
        disabled_list.append(plugin_name)
        plugin_layouts[view_name].insert(-1, plugin_name)
    else:
      if plugin_name in disabled_list:
        disabled_list.remove(plugin_name)
      tab_order = \
          model[iter][self.COL_VIEW].page_num(model[iter][self.COL_INSTANCE])
      try:
        plugin_layouts[view_name].insert(tab_order, plugin_name)
      except KeyError:
        plugin_layouts[view_name] = []
        plugin_layouts[view_name].insert(tab_order, plugin_name)

  def _viewsStoreModify(self, model, iter, column):
    child_model_iter = model.convert_iter_to_child_iter(iter)
    if column == self.VIEWSTORE_VIEW:
      return self[child_model_iter][self.COL_VIEW]
    elif column == self.VIEWSTORE_NAME:
      return getattr(self[child_model_iter][self.COL_VIEW], 'view_name', '')

  def _getViewNames(self):
    return [row[self.VIEWSTORE_NAME] for row in self.views_store]

  def _getViewInstances(self):
    return [row[self.VIEWSTORE_VIEW] for row in self.views_store]

  def _getViewNameInstanceDict(self):
    rv = {}
    for row in self.views_store:
      rv[row[self.VIEWSTORE_NAME]] = row[self.VIEWSTORE_VIEW]
    return rv

class PluginErrorManager(object):
  def __init__(self, notebook):
    self.errors = []
    self.notebook = notebook
    tooltip = gtk.Tooltips()
    tooltip.force_window()
    tooltip.tip_window.ensure_style()
    self.message_style = tooltip.tip_window.rc_get_style()
    self.vbox = None
    self.scrolled_window = None

  def _newErrorTab(self):
    self.scrolled_window = gtk.ScrolledWindow()
    self.scrolled_window.set_name(_('Plugin Errors'))
    self.vbox = gtk.VBox()
    self.scrolled_window.add_with_viewport(self.vbox)
    self.notebook.append_page(self.scrolled_window)
    self.notebook.set_tab_reorderable(self.scrolled_window, False)
    self.notebook.set_tab_detachable(self.scrolled_window, False)
    self.scrolled_window.show_all()
    self.keepOnTop()

  def newError(self, error_message, details):
    if not self.vbox:
      self._newErrorTab()
    plugin_error_message = PluginErrorMessage(error_message, details)
    plugin_error_message.add_button(gtk.STOCK_REFRESH, gtk.RESPONSE_APPLY)
    plugin_error_message.connect('response', self._onResponse)
    self.vbox.pack_start(plugin_error_message, False)
    plugin_error_message.show_all()
    return plugin_error_message

  def keepOnTop(self):
    if self.scrolled_window:
      self.notebook.reorder_child(self.scrolled_window, 0)
      self.notebook.set_current_page(0)

  def _onResponse(self, plugin_message, response_id):
    if response_id == gtk.RESPONSE_CLOSE:
      self.vbox.remove(plugin_message)
      if not self.vbox.get_children():
        self.notebook.remove(self.scrolled_window)
        self.viewport = None
        self.vbox = None

class PluginMapping(object):
  def __init__(self):
    self.gconf_client = gconf.client_get_default()
  def __len__(self):
    view_dirs = self.gconf_client.all_dirs(GCONF_PLUGINVIEWS)
    return len(view_dirs)
  def __getitem__(self, key):
    view_dirs = self.gconf_client.all_dirs(GCONF_PLUGINVIEWS)
    for dir in view_dirs:
      if key == gconf.unescape_key(dir.split('/')[-1], 
                                   len(dir.split('/')[-1])):
        return GConfListWrapper(dir+'/layout')
    raise KeyError, key
  def __setitem__(self, key, value):
    gconf_key = '%s/%s/layout' % \
        (GCONF_PLUGINVIEWS, gconf.escape_key(key, len(key)))
    self.gconf_client.set_list(gconf_key, gconf.VALUE_STRING, value)
  def __iter__(self):
    view_dirs = self.gconf_client.all_dirs(GCONF_PLUGINVIEWS)
    for dir in view_dirs:
      yield gconf.unescape_key(dir.split('/')[-1], len(dir.split('/')[-1]))

class PluginTreeView(gtk.TreeView):
  def __init__(self, plugin_manager):
    gtk.TreeView.__init__(self)
    self.plugin_manager = plugin_manager
    self.set_model(plugin_manager.plugins_store)
    self.connect('button-press-event', self._onButtonPress)
    self.connect('popup-menu', self._onPopupMenu)

    crc = gtk.CellRendererToggle()
    crc.connect('toggled', self._onPluginToggled)
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crc, True)
    tvc.set_cell_data_func(crc, self._pluginStateDataFunc)
    self.append_column(tvc)

    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Name'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=plugin_manager.COL_NAME)
    tvc.set_cell_data_func(crt, self._pluginNameDataFunc)
    self.append_column(tvc)

    crc = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('View'))
    tvc.pack_start(crc, False)
    tvc.set_cell_data_func(crc, self._viewNameDataFunc)
    crc.set_property('editable', True)
    crc.connect('edited', self._onViewChanged)
    self.append_column(tvc)

  def _onButtonPress(self, widget, event):
    if event.button == 3:
      path = self.get_path_at_pos(int(event.x), int(event.y))[0]
      self._showPopup(event.button, event.time, path)
      
  def _onPopupMenu(self, widget):
    path, col = self.get_cursor()
    gdkwindow = self.window
    x, y = self.allocation.x, self.allocation.y
    while gdkwindow:
      window_x, window_y = gdkwindow.get_position()
      x += window_x
      y += window_y
      gdkwindow = gdkwindow.get_parent()
    rect = self.get_cell_area(path, col)
    rect.x, rect.y = self.tree_to_widget_coords(rect.x, rect.y)
    rect.x += x
    rect.y += y
    self._showPopup(0, gtk.get_current_event_time(), 
                    path, lambda m, r: (r.x, r.y, True), rect)
    return True


  def _showPopup(self, button, time, path, pos_func=None, data=None):
    plugin = \
        self.plugin_manager.plugins_store[path][self.plugin_manager.COL_INSTANCE]
    menu = PluginViewMenu(self.plugin_manager, plugin, self.get_toplevel())
    menu.popup(None, None, pos_func, button, time, data)

  def _viewNameDataFunc(self, column, cell, model, iter):
    cell.set_property('text', 
                      _(getattr(model[iter][self.plugin_manager.COL_VIEW],                                       'view_name', '')))

  def _pluginNameDataFunc(self, column, cell, model, iter):
    localized_name = model[iter][self.plugin_manager.COL_LOCALIZED] or \
        model[iter][self.plugin_manager.COL_NAME]
    cell.set_property('text', localized_name)

  def _pluginStateDataFunc(self, column, cell, model, iter):
    cell.set_property('active', 
                      bool(model[iter][self.plugin_manager.COL_INSTANCE]))

  def _onPluginToggled(self, renderer_toggle, path):
    '''
    Callback for a "toggled" signal from a L{gtk.CellRendererToggle} in the
    plugin dialog. Passes along the toggle request to the L{PluginManager}.

    @param renderer_toggle: The toggle cellrenderer that emitted the signal.
    @type renderer_toggle: L{gtk.CellRendererToggle}
    @param path: The path that has been toggled.
    @type path: tuple
    '''
    self.plugin_manager.togglePlugin(path)

  def _onViewChanged(self, cellrenderertext, path, new_text):
    '''
    Callback for an "edited" signal from a L{gtk.CellRendererCombo} in the
    plugin dialog. Passes along the new requested view name to the L{PluginManager}.

    @param cellrenderertext: The combo cellrenderer that emitted the signal.
    @type renderer_toggle: L{gtk.CellRendererCombo}
    @param path: The path that has been touched.
    @type path: tuple
    @param new_text: The new text that has been entered in to the combo entry.
    @type new_text: string
    '''
    plugin = \
        self.plugin_manager.plugins_store[path][self.plugin_manager.COL_INSTANCE]
    self.plugin_manager.changeView(plugin, new_text)

class PluginViewMenu(gtk.Menu):
  RADIO_GROUP = 13
  def __init__(self, plugin_manager, context_plugin, transient_window):
    gtk.Menu.__init__(self)
    self.plugin_manager = plugin_manager
    self._buildMenu(context_plugin, transient_window)
  
  def _buildMenu(self, context_plugin, transient_window):
    menu_item = None
    for view, view_name in self.plugin_manager.views_store:
      menu_item = gtk.RadioMenuItem(menu_item, view_name)
      menu_item.connect('toggled', self._onItemToggled, view, context_plugin)
      menu_item.set_active(view == context_plugin.parent)
      self.append(menu_item)
      menu_item.show()
    menu_item = gtk.SeparatorMenuItem()
    self.append(menu_item)
    menu_item.show()
    menu_item = gtk.MenuItem(_('<i>_New view...</i>'))
    menu_item.child.set_use_markup(True)
    menu_item.connect('activate', self._onItemActivated, 
                      context_plugin, transient_window)
    self.append(menu_item)
    menu_item.show()
      
  def _onItemToggled(self, menu_item, view, context_plugin):
    self.plugin_manager.changeView(context_plugin, view.view_name)

  def _onItemActivated(self, menu_item, context_plugin, transient_window):
    new_view_dialog = PluginNewViewDialog(self.plugin_manager, transient_window)
    response_id = new_view_dialog.run()
    plugin_name = new_view_dialog.getEntryText()
    if response_id == gtk.RESPONSE_OK and plugin_name:
      self.plugin_manager.changeView(context_plugin, plugin_name)
    new_view_dialog.destroy()

class PluginNewViewDialog(gtk.Dialog):
  def __init__(self, plugin_manager, transient_window):
    self.plugin_manager = plugin_manager
    gtk.Dialog.__init__(self, _('New View...'), transient_window)
    self.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK,
                     gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
    self.set_default_response(gtk.RESPONSE_OK)
    completion = gtk.EntryCompletion()
    completion.set_model(self.plugin_manager.views_store)
    completion.set_text_column(self.plugin_manager.VIEWSTORE_NAME)
    self.entry = gtk.Entry()
    self.entry.set_completion(completion)
    self.entry.connect('activate', self._onEntryActivate)
    self.vbox.add(self.entry)
    self.entry.show()

  def getEntryText(self):
    return self.entry.get_text()

  def _onEntryActivate(self, entry):
    self.response(gtk.RESPONSE_OK)
