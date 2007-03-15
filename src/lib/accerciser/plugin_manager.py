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
import plugin as accerciser_plugin
from plugin import PluginErrorMessage
from tools import Tools
import pyLinAcc
import os
import sys
import imp
import pango
import traceback

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
    elif isinstance(child, accerciser_plugin.Plugin):
      name = child.plugin_name
    elif child.name:
      name = child.name
    gtk.Notebook.insert_page(self, child, gtk.Label(name), position=position)
    self.set_tab_detachable(child, True)
    self.set_tab_reorderable(child, True)

  def append_page(self, child, tab_label=None):
    self.insert_page(child, tab_label, -1)

  def prepend_page(self, child, tab_label=None):
    self.insert_page(child, tab_label, 0)



class PluginViewWindow(gtk.Window, Tools):
  def __init__(self, view_name):
    gtk.Window.__init__(self)
    self.plugin_view = PluginView(view_name)
    self.add(self.plugin_view)
    view_dimensions = self.loadSettings('plugin_view_sizes') or {}
    window_size = view_dimensions.get(view_name.lower(), (480, 480))
    self.connect('key_press_event', self._onKeyPress)
    self.set_default_size(window_size[0], window_size[1])
    self.set_title(view_name)
    self.set_position(gtk.WIN_POS_MOUSE)
    self.show_all()

  def _onKeyPress(self, widget, event):
    if event.state & gtk.gdk.MOD1_MASK and \
          event.keyval in xrange(gtk.gdk.keyval_from_name('0'), 
                                 gtk.gdk.keyval_from_name('9')):
      tab_num = event.keyval - gtk.gdk.keyval_from_name('0') or 10
      pages_count = self.plugin_view.get_n_pages()
      if pages_count >= tab_num:
        self.plugin_view.set_current_page(tab_num - 1)
      
  
class PluginManager(gobject.GObject, Tools):
  def __init__(self, node, pluginviews_main):
    gobject.GObject.__init__(self)
    self.node = node
    self.pluginviews_main = pluginviews_main
    self._restorePanedViews(pluginviews_main)
    self.views_store = gtk.ListStore(PluginView, str)
    for view in pluginviews_main:
      self.views_store.append([view, view.view_name])
    self.plugins_store = gtk.ListStore(str, # Plugin name
                                       str, # Plugin description
                                       str, # View name
                                       object, # Plugin instance
                                       bool, # Plugin state
                                       str, # Plugin class name
                                       str, # Plugin file name
                                       str) # Plugin path
    for i, col in enumerate(['NAME', 'DESC', 'VIEW', 'INSTANCE',
                             'STATE', 'CLASS', 'FILE', 'PATH']):
      setattr(self.plugins_store, 'COL_'+col, i)
    self.disabled_plugins = {}
    self.closed = False
    self.error_manager = PluginErrorManager(self.pluginviews_main[-1])

  def close(self):
    self._saveViewDimensions()
    self._saveLayout()
    for row in self.plugins_store:
      plugin = row[self.plugins_store.COL_INSTANCE]
      if plugin:
        plugin._close()
    self.closed = True

  def loadPlugins(self):
    plugin_layout = self._loadLayout()
    plugin_dir_local = os.path.join(os.environ['HOME'], 
                                    '.accerciser', 'plugins')
    plugin_dir_global = os.path.join(sys.prefix, 'share',
                                     'accerciser', 'plugins')
    plugin_list = []
    for plugin_dir in (plugin_dir_local, plugin_dir_global):
      if not os.path.isdir(plugin_dir):
        continue
      for fn in os.listdir(plugin_dir):
        if fn.endswith('.py') and not fn.startswith('.'):
          self._loadPluginFile(plugin_dir, fn[:-3],
                               plugin_layout)
    for view, view_name in self.views_store:
      for child in view.get_children():
        if isinstance(child, accerciser_plugin.Plugin):
          plugin = child
          view.reorder_child(child, 
                             plugin_layout.get(plugin.plugin_name.lower(),
                                               [None,-1])[1])
      self._connectSignals(view)
      view.set_current_page(0)
      view.show_all()
    self.error_manager.keepOnTop()

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
      plugin_layout = self._loadLayout()
      self._loadPluginFile(plugin_file_info[0], 
                           plugin_file_info[1], 
                           plugin_layout)
      error_message.emit('response', gtk.RESPONSE_CLOSE)

  def _loadPluginFile(self, plugin_dir, plugin_fn, plugin_layout):
    plugin_locals = self._getPluginLocals(plugin_dir, plugin_fn)
    # use keys list to avoid size changes during iteration
    for symbol in plugin_locals.keys():
      try:
        is_plugin = issubclass(plugin_locals[symbol],
                               accerciser_plugin.Plugin)
      except TypeError:
        continue
      if is_plugin:
        view_name = self._getViewNameForPlugin(plugin_locals[symbol].plugin_name,
                                               plugin_layout)
        try:
          iter = self.plugins_store.append([plugin_locals[symbol].plugin_name,
                                            plugin_locals[symbol].plugin_description,
                                            view_name, None, False, symbol,
                                            plugin_fn, plugin_dir])
        except AttributeError, e:
          error_message = self.error_manager.newError(
            traceback.format_exception_only(e.__class__, e)[0].strip(),
            traceback.format_exc())
          error_message.connect('response', self._onRetryFileLoad, 
                                (plugin_dir, plugin_fn))
          continue
        # if a plugin class is found, initialize
        if plugin_layout.get(plugin_locals[symbol].plugin_name.lower(), 
                             [None,None,True])[2]:
          self._enablePlugin(plugin_locals, iter)

  def _enablePlugin(self, plugin_locals, iter, set_current=False):
    plugin_class = plugin_locals.get(
      self.plugins_store[iter][self.plugins_store.COL_CLASS])
    try:
      plugin_instance = plugin_class(self.node)
      plugin_instance.init()
      plugin_instance.onAccChanged(plugin_instance.node.acc)
    except Exception, e:
      error_message = self.error_manager.newError(
        traceback.format_exception_only(e.__class__, e)[0].strip(),
        traceback.format_exc())
      error_message.connect('response', self._onRetryPluginEnable, iter)
      return
    self.plugins_store[iter][self.plugins_store.COL_STATE] = True
    self.plugins_store[iter][self.plugins_store.COL_INSTANCE] = plugin_instance
    if isinstance(plugin_instance, gtk.Widget):
      view_name = self.plugins_store[iter][self.plugins_store.COL_VIEW]
      pluginview = self._getViewByName(view_name)
      plugin_instance.connect('reload-request', self._onReloadRequest)
      self._addPluginToView(pluginview, plugin_instance)
      if set_current:
        pluginview.set_current_page(-1)

  def _disablePlugin(self, iter):
    plugin_instance = self.plugins_store[iter][self.plugins_store.COL_INSTANCE]
    if not plugin_instance: return
    if isinstance(plugin_instance, gtk.Widget):
      plugin_instance.destroy()
    plugin_instance._close()
    self.plugins_store[iter][self.plugins_store.COL_STATE] = False
    self.plugins_store[iter][self.plugins_store.COL_INSTANCE] = None

  def _reloadPlugin(self, iter):
    plugin_fn = self.plugins_store[iter][self.plugins_store.COL_FILE]
    plugin_dir = self.plugins_store[iter][self.plugins_store.COL_PATH]
    plugin_locals = self._getPluginLocals(plugin_dir, plugin_fn)
    self._enablePlugin(plugin_locals, iter, True)
    return self.plugins_store[iter][self.plugins_store.COL_INSTANCE]

  def _onRetryPluginEnable(self, error_message, response_id, iter):
    if response_id == gtk.RESPONSE_APPLY:
      self._reloadPlugin(iter)
      error_message.emit('response', gtk.RESPONSE_CLOSE)

  def _onReloadRequest(self, plugin):
    iter = None
    for row in self.plugins_store:
      if row[self.plugins_store.COL_INSTANCE] == plugin:
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
    if self.plugins_store[path][self.plugins_store.COL_STATE]:
      # Disable plugin
      self._disablePlugin(self.plugins_store.get_iter(path))
    else:
      # Enable plugin
      self._reloadPlugin(self.plugins_store.get_iter(path))

  def _getViewNameForPlugin(self, name, plugin_layout):
    return plugin_layout.get(name.lower(), 
                             [self.pluginviews_main[0].view_name])[0]

  def _getViewByName(self, view_name):
    if view_name not in [row[1] for row in self.views_store]:
      w = PluginViewWindow(view_name)
      w.connect('delete_event', self._onPluginViewRemoved)
      self.views_store.append([w.plugin_view, view_name])
      return w.plugin_view
    else:
      for view, view_name2 in self.views_store:
        if view_name2 == view_name:
          return view

  def _addPluginToView(self, view, plugin):
    view.append_page(plugin)
    plugin.show_all()
    
  def _connectSignals(self, pluginview):
    pluginview.connect('new_view', self._onNewPluginView)
    pluginview.connect('page_added', self._onPluginLayoutChanged)
    pluginview.connect('page_removed', self._onPluginLayoutChanged)
    pluginview.connect('page_reordered', self._onPluginLayoutChanged)

  def _onNewPluginView(self, view, child):
    view.remove(child)
    self._newViewWithPage(child)

  def _newViewWithPage(self, page, view_name=None):
    if not view_name:
      view_name = 'Plugin View'
      view_num = 2
      while view_name in [row[1] for row in self.views_store]:
        view_name = 'Plugin View (%d)' % view_num
        view_num += 1
    w = PluginViewWindow(view_name)
    w.connect('delete_event', self._onPluginViewRemoved)
    pluginview = w.plugin_view
    self._connectSignals(pluginview)
    self.views_store.append([pluginview, view_name])
    pluginview.append_page(page)

  def _onPluginViewRemoved(self, pluginviewwindow, event):
    pluginview = pluginviewwindow.plugin_view
    for child in pluginview.get_children():
      pluginview.remove(child)
      self.pluginviews_main[0].append_page(child)

  def _onPluginLayoutChanged(self, pluginview, page, page_num):
    if self.closed:
      return
    iter = self.views_store.get_iter_root()
    while iter:
      view = self.views_store[iter][0]
      if view.get_n_pages() > 0 or view in self.pluginviews_main:
        iter = self.views_store.iter_next(iter)
      else:
        if view.get_n_pages() == 0:
          self._onPluginViewRemoved(view.parent, None)
          view.parent.destroy()
        if not self.views_store.remove(iter): break
    iter = self.plugins_store.get_iter_root()
    for row in self.plugins_store:
      plugin = row[self.plugins_store.COL_INSTANCE]
      if plugin:
        view = plugin.parent
        if view:
          row[self.plugins_store.COL_VIEW] = view.view_name
    
  def _loadLayout(self):
    # TODO: create a default system-wide default configuration for stuff 
    # like this.
    rv = {'ipython console' : ('Bottom panel', 0, True),
          'interface viewer' : ('Top right', 0, True),
          'event monitor' : ('Top right', 1, True),
          'api browser' : ('Top right', 2, True)}
    layout = self.loadSettings('plugin_layout') or {}
    rv.update(layout)
    return rv

  def _saveLayout(self):
    layout = {}
    for row in self.plugins_store:
      view_name = row[self.plugins_store.COL_VIEW]
      plugin_name = row[self.plugins_store.COL_NAME]
      plugin_instance = row[self.plugins_store.COL_INSTANCE]
      state = row[self.plugins_store.COL_STATE]
      if plugin_instance:
        tab_order = plugin_instance.parent.page_num(plugin_instance)
      else:
        tab_order = -1
      layout[plugin_name] = (view_name, tab_order, state)
    self.saveSettings('plugin_layout', layout)
    

  def _saveViewDimensions(self):
    view_dimensions = {}
    for view, view_name in self.views_store:
      child = view
      while child:
        if isinstance(child.parent, PluginViewWindow):
          window = child.parent
          view_dimensions[view_name] = (window.allocation.width, 
                                        window.allocation.height)
          break
        elif isinstance(child.parent, gtk.Paned):
          paned = child.parent
          view_dimensions[view_name] = (paned.get_position(),)
          break
        child = child.parent
    self.saveSettings('plugin_view_sizes', view_dimensions)
  
  def _restorePanedViews(self, views):
    view_dimensions = self.loadSettings('plugin_view_sizes') or {}
    for view in views:
      if not view_dimensions.has_key(view.view_name.lower()):
        continue
      child = view
      while child:
        if isinstance(child.parent, gtk.Paned):
          paned = child.parent
          paned.set_position(view_dimensions[view.view_name.lower()][0])
          break
        child = child.parent

  def changeView(self, path, new_text):
    plugin = self.plugins_store[path][3]
    old_view = plugin.parent
    view_names = [v[1] for v in self.views_store]
    try:
      view = self.views_store[view_names.index(new_text)][0]
    except ValueError:
      old_view.remove(plugin)
      self._newViewWithPage(plugin, new_text)
    else:
      if plugin in view.get_children():
        return
      else:
        old_view.remove(plugin)
        view.append_page(plugin)    

class PluginErrorManager(object):
  plugin_name = 'Plugin Errors'
  plugin_description = \
      'A built-in plugin for displaying errors of other plugins'
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
    self.scrolled_window.set_name('Plugin Errors')
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

