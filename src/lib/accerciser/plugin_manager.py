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
from plugin import Plugin
from view_manager import ViewManager
from tools import Tools, GConfListWrapper
from message import MessageManager
import os
import sys
import imp
import pango
import traceback
import gconf
from i18n import _, N_

GCONF_PLUGIN_DISABLED = '/apps/accerciser/disabled_plugins'      

class PluginManager(gtk.ListStore, Tools):
  COL_INSTANCE = 0
  COL_CLASS = 1
  COL_PATH = 2
  def __init__(self, node, hotkey_manager, *main_views):
    gtk.ListStore.__init__(self,
                           object, # Plugin instance
                           object, # Plugin class
                           str) # Plugin path
    self.node = node
    self.gconf_client = gconf.client_get_default()
    self.hotkey_manager = hotkey_manager
    self.view_manager = ViewManager(*main_views)
    self.message_manager = MessageManager()
    self.message_manager.connect('plugin-reload-request', 
                                 self._onPluginReloadRequest)
    self.message_manager.connect('module-reload-request', 
                                 self._onModuleReloadRequest)
    message_tab = self.message_manager.getMessageTab()
    self.view_manager.addElement(message_tab)
    self._row_changed_handler = \
        self.connect('row_changed', self._onPluginRowChanged)
    self._loadPlugins()

  def close(self):
    self.view_manager.close()
    for row in self:
      plugin = row[self.COL_INSTANCE]
      if plugin:
        plugin._close()

  def _loadPlugins(self):
    for plugin_dir, plugin_fn in self._getPluginFiles():
      self._loadPluginFile(plugin_dir, plugin_fn)
    self.view_manager.initialView()

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

  def _getPluginLocals(self, plugin_dir, plugin_fn):
    sys.path.insert(0, plugin_dir)
    try:
      params = imp.find_module(plugin_fn, [plugin_dir])
      plugin = imp.load_module(plugin_fn, *params)
      plugin_locals = plugin.__dict__
    except Exception, e:
      self.message_manager.newModuleError(plugin_fn, plugin_dir,
        traceback.format_exception_only(e.__class__, e)[0].strip(),
        traceback.format_exc())
      return {}
    sys.path.pop(0)
    return plugin_locals

  def _loadPluginFile(self, plugin_dir, plugin_fn):
    plugin_locals = self._getPluginLocals(plugin_dir, plugin_fn)
    # use keys list to avoid size changes during iteration
    for symbol in plugin_locals.keys():
      try:
        is_plugin = \
            issubclass(plugin_locals[symbol], Plugin) and \
            getattr(plugin_locals[symbol], 'plugin_name', None)
      except TypeError:
        continue
      if is_plugin:
        self.handler_block(self._row_changed_handler)
        iter = self.append([None, plugin_locals[symbol], plugin_dir])
        self.handler_unblock(self._row_changed_handler)
        # if a plugin class is found, initialize
        enabled = plugin_locals[symbol].plugin_name not in \
            GConfListWrapper(GCONF_PLUGIN_DISABLED)
        if enabled:
          self._enablePlugin(plugin_locals, iter)
        self.row_changed(self.get_path(iter), iter)

  def _enablePlugin(self, plugin_locals, iter, set_current=False):
    plugin_class = self[iter][self.COL_CLASS]
    plugin_instance = None
    try:
      plugin_instance = plugin_class(self.node, self.message_manager)
      plugin_instance.init()
      for key_combo in plugin_instance.global_hotkeys:
        self.hotkey_manager.addKeyCombo(
          plugin_class.plugin_name, 
          plugin_class.plugin_name_localized or plugin_class.plugin_name
          , *key_combo)
    except Exception, e:
      self.message_manager.newPluginError(
        plugin_instance, plugin_class,
        traceback.format_exception_only(e.__class__, e)[0].strip(),
        traceback.format_exc())
      try:
        plugin_instance._close()
      except:
        pass
      return
    self[iter][self.COL_INSTANCE] = plugin_instance
    if isinstance(plugin_instance, gtk.Widget):
      self.view_manager.addElement(plugin_instance)
    plugin_instance.onAccChanged(plugin_instance.node.acc)
      #plugin_instance.show_all()

  def _disablePlugin(self, iter):
    plugin_instance = self[iter][self.COL_INSTANCE]
    if not plugin_instance: return
    for key_combo in plugin_instance.global_hotkeys:
      self.hotkey_manager.removeKeyCombo(
        plugin_instance.plugin_name, *key_combo)
    if isinstance(plugin_instance, gtk.Widget):
      plugin_instance.destroy()
    plugin_instance._close()
    self[iter][self.COL_INSTANCE] = None

  def _reloadPlugin(self, iter):
    old_class = self[iter][self.COL_CLASS]
    plugin_fn = old_class.__module__
    plugin_dir = self[iter][self.COL_PATH]
    plugin_locals = self._getPluginLocals(plugin_dir, plugin_fn)
    self[iter][self.COL_CLASS] = plugin_locals.get(old_class.__name__)
    self._enablePlugin(plugin_locals, iter, True)
    return self[iter][self.COL_INSTANCE]

  def _getIterWithClass(self, plugin_class):
    iter = self.get_iter_first()
    while iter:
      if self[iter][self.COL_CLASS] == plugin_class:
        return iter
      iter = self.iter_next(iter)
    return None

  def _onPluginReloadRequest(self, message_manager, message, plugin_class):
    message.destroy()
    iter = self._getIterWithClass(plugin_class)
    if not iter: return
    self._disablePlugin(iter)
    plugin = self._reloadPlugin(iter)
    if plugin:
      self.view_manager.giveElementFocus(plugin)

  def _onModuleReloadRequest(self, message_manager, message, module, path):
    message.destroy()
    self._loadPluginFile(path, module)

  def togglePlugin(self, path):
    iter = self.get_iter(path)
    if self[iter][self.COL_INSTANCE]:
      self._disablePlugin(iter)
    else:
      self._reloadPlugin(iter)

  def _getIterFromPlugin(self, plugin):
    for row in self:
      if row[self.COL_INSTANCE] == plugin:
        return row.iter
    return None
  
  def _onPluginRowChanged(self, model, path, iter):
    plugin_class = model[iter][self.COL_CLASS]
    if plugin_class is None:
      return
    plugin_instance = model[iter][self.COL_INSTANCE]
    disabled_list = GConfListWrapper(GCONF_PLUGIN_DISABLED)
    if plugin_instance is None:
      if plugin_class.plugin_name not in disabled_list:
        disabled_list.append(plugin_class.plugin_name)
    else:
      if plugin_class.plugin_name in disabled_list:
        disabled_list.remove(plugin_class.plugin_name)

  def View(self):
    return self._View(self)

  class _View(gtk.TreeView):
    def __init__(self, plugin_manager):
      gtk.TreeView.__init__(self)
      self.plugin_manager = plugin_manager
      self.view_manager = plugin_manager.view_manager
      self.set_model(plugin_manager)
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
          self.plugin_manager[path][self.plugin_manager.COL_INSTANCE]
      menu = self.view_manager.Menu(plugin, self.get_toplevel())
      menu.popup(None, None, pos_func, button, time, data)

    def _viewNameDataFunc(self, column, cell, model, iter):
      plugin_class = model[iter][self.plugin_manager.COL_CLASS]
      view_name = \
          self.view_manager.getViewNameForPlugin(plugin_class.plugin_name)
      cell.set_property('text', _(view_name))

    def _pluginNameDataFunc(self, column, cell, model, iter):
      plugin_class = model[iter][self.plugin_manager.COL_CLASS]
      cell.set_property('text', plugin_class.plugin_name_localized or \
                          plugin_class.plugin_name)

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
          self.plugin_manager[path][self.plugin_manager.COL_INSTANCE]
      self.view_manager.changeView(plugin, new_text)
