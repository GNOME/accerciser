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

import gi

from gi.repository import GLib
from gi.repository import Gtk as gtk
from gi.repository.Gio import Settings as GSettings

from .base_plugin import Plugin
from .view import ViewManager
from accerciser.tools import ToolsAccessor, getTreePathBoundingBox
from .message import MessageManager
import os
import sys
import importlib
import traceback
from accerciser.i18n import _, N_, C_

GSCHEMA = 'org.a11y.Accerciser'

class PluginManager(gtk.ListStore, ToolsAccessor):
  '''

  @cvar COL_INSTANCE: Instance column ID.
  @type COL_INSTANCE: integer
  @cvar COL_CLASS: Class column ID.
  @type COL_CLASS: integer
  @cvar COL_PATH: Module path column ID.
  @type COL_PATH: integer

  @ivar node: Application's selected accessible node.
  @type node: L{Node}
  @ivar hotkey_manager: Application's hotkey manager.
  @type hotkey_manager: L{HotkeyManager}
  @ivar view_manager: Plugin view manager.
  @type view_manager: L{ViewManager}
  @ivar message_manager: Plugin message manager.
  @type message_manager: L{MessageManager}

  '''
  COL_INSTANCE = 0
  COL_CLASS = 1
  COL_PATH = 2
  def __init__(self, application, node, hotkey_manager, *main_views):
    '''
    Initialize the plugin manager.

    @param application: The application.
    @type application: gtk.Application.
    @param node: The application's main node.
    @type node: L{Node}
    @param hotkey_manager: Application's hot key manager.
    @type hotkey_manager: L{HotkeyManager}
    @param main_views: List of permanent plugin views.
    @type main_views: list of {PluginView}
    '''
    gtk.ListStore.__init__(self,
                           object, # Plugin instance
                           object, # Plugin class
                           str) # Plugin path
    self.node = node
    self.hotkey_manager = hotkey_manager
    self.gsettings = GSettings.new(GSCHEMA)
    self.view_manager = ViewManager(application, *main_views)
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
    '''
    Close view manager and plugins.
    '''
    self.view_manager.close()
    for row in self:
      plugin = row[self.COL_INSTANCE]
      if plugin:
        plugin._close()

  def _loadPlugins(self):
    '''
    Load all plugins in global and local plugin paths.
    '''
    # AQUI PETAA
    for plugin_dir, plugin_fn in self._getPluginFiles():
      self._loadPluginFile(plugin_dir, plugin_fn)
    self.view_manager.initialView()

  def _getPluginFiles(self):
    '''
    Get list of all modules in plugin paths.

    @return: List of plugin files with their paths.
    @rtype: tuple
    '''
    plugin_file_list = []
    plugin_dir_local = os.path.join(GLib.get_user_data_dir(),
                                    'accerciser', 'plugins')
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
    '''
    Get namespace of given module

    @param plugin_dir: Path.
    @type plugin_dir: string
    @param plugin_fn: Module.
    @type plugin_fn: string

    @return: Dictionary of modules symbols.
    @rtype: dictionary
    '''
    sys.path.insert(0, plugin_dir)
    try:
      plugin = importlib.import_module(plugin_fn)
      plugin_locals = plugin.__dict__
    except Exception as e:
      self.message_manager.newModuleError(plugin_fn, plugin_dir,
        traceback.format_exception_only(e.__class__, e)[0].strip(),
        traceback.format_exc())
      return {}
    sys.path.pop(0)
    return plugin_locals

  def _loadPluginFile(self, plugin_dir, plugin_fn):
    '''
    Find plugin implementations in the given module, and store them.

    @param plugin_dir: Path.
    @type plugin_dir: string
    @param plugin_fn: Module.
    @type plugin_fn: string
    '''
    plugin_locals = self._getPluginLocals(plugin_dir, plugin_fn)
    # use keys list to avoid size changes during iteration
    for symbol in list(plugin_locals.keys()):
      try:
        is_plugin = \
            issubclass(plugin_locals[symbol], Plugin) and \
            getattr(plugin_locals[symbol], 'plugin_name', None)
      except TypeError:
        continue
      if is_plugin:
        self.handler_block(self._row_changed_handler)

        iter_id = self.append([None, plugin_locals[symbol], plugin_dir])
        self.handler_unblock(self._row_changed_handler)
        # if a plugin class is found, initialize
        disabled_list = self.gsettings.get_strv('disabled-plugins')
        enabled = plugin_locals[symbol].plugin_name not in \
            disabled_list
        if enabled:
          self._enablePlugin(iter_id)
        self.row_changed(self.get_path(iter_id), iter_id)

  def _enablePlugin(self, iter):
    '''
    Instantiate a plugin class pointed to by the given iter.

    @param iter: Iter of plugin class we should instantiate.
    @type iter: gtk.TreeIter
    '''
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
    except Exception as e:
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
    disabled_list = self.gsettings.get_strv('disabled-plugins')
    if plugin_instance.plugin_name in disabled_list:
      disabled_list.remove(plugin_instance.plugin_name)
      self.gsettings.set_strv('disabled-plugins', disabled_list)

  def _disablePlugin(self, iter):
    '''
    Disable plugin pointed to by the given iter.

    @param iter: Iter of plugin instance to be disabled.
    @type iter: gtk.TreeIter
    '''
    plugin_instance = self[iter][self.COL_INSTANCE]
    if not plugin_instance: return
    for key_combo in plugin_instance.global_hotkeys:
      self.hotkey_manager.removeKeyCombo(
        plugin_instance.plugin_name, *key_combo)
    if isinstance(plugin_instance, gtk.Widget):
      plugin_instance.destroy()
    plugin_instance._close()

    disabled_list = self.gsettings.get_strv('disabled-plugins')
    if not plugin_instance.plugin_name in disabled_list:
      disabled_list.append(plugin_instance.plugin_name)
    self.gsettings.set_strv('disabled-plugins', disabled_list)

    self[iter][self.COL_INSTANCE] = False

  def _reloadPlugin(self, iter):
    '''
    Reload plugin pointed to by the given iter.

    @param iter: Iter of plugin to be reloaded.
    @type iter: gtk.TreeIter

    @return: New instance of plugin
    @rtype: L{Plugin}
    '''
    old_class = self[iter][self.COL_CLASS]
    plugin_fn = old_class.__module__
    plugin_dir = self[iter][self.COL_PATH]
    plugin_locals = self._getPluginLocals(plugin_dir, plugin_fn)
    self[iter][self.COL_CLASS] = plugin_locals.get(old_class.__name__)
    self._enablePlugin(iter)
    return self[iter][self.COL_INSTANCE]

  def _getIterWithClass(self, plugin_class):
    '''
    Get iter with given plugin class.

    @param plugin_class: The plugin class to search for.
    @type plugin_class: type

    @return: The first iter with the given class.
    @rtype: gtk.TreeIter
    '''
    for row in self:
      if row[self.COL_CLASS] == plugin_class:
        return row.iter
    return None

  def _onPluginReloadRequest(self, message_manager, message, plugin_class):
    '''
    Callback for a plugin reload request from the message manager.

    @param message_manager: The message manager that emitted the signal.
    @type message_manager: L{MessageManager}
    @param message: The message widget.
    @type message: L{PluginMessage}
    @param plugin_class: The plugin class that should be reloaded.
    @type plugin_class: type
    '''
    message.destroy()
    iter = self._getIterWithClass(plugin_class)
    if not iter: return
    self._disablePlugin(iter)
    plugin = self._reloadPlugin(iter)
    if plugin:
      self.view_manager.giveElementFocus(plugin)

  def _onModuleReloadRequest(self, message_manager, message, module, path):
    '''
    Callback for a module reload request from the message manager.

    @param message_manager: The message manager that emitted the signal.
    @type message_manager: L{MessageManager}
    @param message: The message widget.
    @type message: L{PluginMessage}
    @param module: The module to be reloaded.
    @type module: string
    @param path: The path of the module.
    @type path: string
    '''
    message.destroy()
    self._loadPluginFile(path, module)

  def togglePlugin(self, path):
    '''
    Toggle the plugin, either enable or disable depending on current state.

    @param path: Tree path to plugin.
    @type path: tuple
    '''
    iter = self.get_iter(path)
    if self[iter][self.COL_INSTANCE]:
      self._disablePlugin(iter)
    else:
      self._reloadPlugin(iter)

  def _onPluginRowChanged(self, model, path, iter):
    '''
    Callback for model row changes. Persists plugins state (enabled/disabled)
    in gsettings.

    @param model: Current model, actually self.
    @type model: gtk.ListStore
    @param path: Tree path of changed row.
    @type path: tuple
    @param iter: Iter of changed row.
    @type iter: gtk.TreeIter
    '''
    plugin_class = model[iter][self.COL_CLASS]
    if plugin_class is None:
      return
    plugin_instance = model[iter][self.COL_INSTANCE]
    disabled_list = self.gsettings.get_strv('disabled-plugins')
    if plugin_instance is None:
      if plugin_class.plugin_name not in disabled_list:
        disabled_list.append(plugin_class.plugin_name)
    else:
      if plugin_class.plugin_name in disabled_list:
        disabled_list.remove(plugin_class.plugin_name)

  def View(self):
    '''
    Helps emulate a non-static inner class. These don't exist in python,
    I think.

    @return: An inner view class.
    @rtype: L{PluginManager._View}
    '''
    return self._View(self)

  class _View(gtk.TreeView):
    '''
    Implements a treeview of a {PluginManager}

    @ivar plugin_manager: Plugin manager to use as data model.
    @type plugin_manager: L{PluginManager}
    @ivar view_manager: View manager to use for plugin view data.
    @type view_manager: L{ViewManager}
    '''
    def __init__(self, plugin_manager):
      '''
      Initialize view.

      @param plugin_manager: Plugin manager to use as data model.
      @type plugin_manager: L{PluginManager}
      '''
      gtk.TreeView.__init__(self)
      self.plugin_manager = plugin_manager
      self.view_manager = plugin_manager.view_manager
      self.set_model(plugin_manager)
      self.connect('button-press-event', self._onButtonPress)
      self.connect('popup-menu', self._onPopupMenu)

      crc = gtk.CellRendererToggle()
      tvc = gtk.TreeViewColumn()
      tvc.pack_start(crc, True)
      tvc.set_cell_data_func(crc, self._pluginStateDataFunc)
      crc.connect('toggled', self._onPluginToggled)
      self.append_column(tvc)

      crt = gtk.CellRendererText()
      tvc = gtk.TreeViewColumn(_('Name'))
      tvc.pack_start(crt, True)
      tvc.set_cell_data_func(crt, self._pluginNameDataFunc)
      self.append_column(tvc)

      crc = gtk.CellRendererText()
      # Translators: This is the viewport in which the plugin appears,
      # it is a noun.
      #
      tvc = gtk.TreeViewColumn(C_('viewport', 'View'))
      tvc.pack_start(crc, False)
      tvc.set_cell_data_func(crc, self._viewNameDataFunc)
      crc.set_property('editable', True)
      crc.connect('edited', self._onViewChanged)
      self.append_column(tvc)

    def _onButtonPress(self, widget, event):
      '''
      Callback for plugin view context menus.

      @param widget: Widget that emitted signal.
      @type widget: gtk.Widget
      @param event: Event object.
      @type event: gtk.gdk.Event
      '''
      if event.button == 3:
        path = self.get_path_at_pos(int(event.x), int(event.y))[0]
        self._showPopup(event.button, event.time, path)

    def _onPopupMenu(self, widget):
      '''
      Callback for popup request event. Usually happens when keyboard
      context menu os pressed.

      @param widget: Widget that emitted signal.
      @type widget: gtk.Widget

      @return: Return true to stop event trickling.
      @rtype: boolean
      '''
      path, col = self.get_cursor()
      rect = getTreePathBoundingBox(self, path, col)
      self._showPopup(0, gtk.get_current_event_time(),
                      path, lambda m, r: (r.x, r.y, True), rect)
      return True


    def _showPopup(self, button, time, path, pos_func=None, data=None):
      '''
      Convenience function for showing the view manager's popup menu.

      @param button: Mouse button that was clicked.
      @type button: integer
      @param time: Time of event.
      @type time: float
      @param path: Tree path of context menu.
      @type path: tuple
      @param pos_func: Function to use for determining menu placement.
      @type pos_func: callable
      @param data: Additional data.
      @type data: object
      '''
      plugin = \
          self.plugin_manager[path][self.plugin_manager.COL_INSTANCE]
      menu = self.view_manager.Menu(plugin, self.get_toplevel())
      menu.popup(None, None, pos_func, data, button, time)

    def _viewNameDataFunc(self, column, cell, model, iter, foo=None):
      '''
      Function for determining the displayed data in the tree's view column.

      @param column: Column number.
      @type column: integer
      @param cell: Cellrender.
      @type cell: gtk.CellRendererText
      @param model: Tree's model
      @type model: gtk.ListStore
      @param iter: Tree iter of current row,
      @type iter: gtk.TreeIter
      '''
      plugin_class = model[iter][self.plugin_manager.COL_CLASS]
      if issubclass(plugin_class, gtk.Widget):
        view_name = \
            self.view_manager.getViewNameForPlugin(plugin_class.plugin_name)
        cell.set_property('sensitive', True)
      else:
        view_name = N_('No view')
        cell.set_property('sensitive', False)
      cell.set_property('text', _(view_name))

    def _pluginNameDataFunc(self, column, cell, model, iter, foo=None):
      '''
      Function for determining the displayed data in the tree's plugin column.

      @param column: Column number.
      @type column: integer
      @param cell: Cellrender.
      @type cell: gtk.CellRendererText
      @param model: Tree's model
      @type model: gtk.ListStore
      @param iter: Tree iter of current row,
      @type iter: gtk.TreeIter
      '''
      plugin_class = model[iter][self.plugin_manager.COL_CLASS]
      cell.set_property('text', plugin_class.plugin_name_localized or \
                          plugin_class.plugin_name)

    def _pluginStateDataFunc(self, column, cell, model, iter, foo=None):
      '''
      Function for determining the displayed state of the plugin's checkbox.

      @param column: Column number.
      @type column: integer
      @param cell: Cellrender.
      @type cell: gtk.CellRendererText
      @param model: Tree's model
      @type model: gtk.ListStore
      @param iter: Tree iter of current row,
      @type iter: gtk.TreeIter
      '''
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
      plugin dialog. Passes along the new requested view name to the
      L{PluginManager}.

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
