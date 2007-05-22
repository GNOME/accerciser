'''
Defines and manages the multiple plugin views.

@author: Eitan Isaacson
@organization: Mozilla Foundation
@copyright: Copyright (c) 2006, 2007 Mozilla Foundation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import gtk
import gobject
from plugin import Plugin
from tools import Tools, GConfListWrapper
from plugin_manager import *
from message import MessageManager
import os
import sys
import imp
import pango
import traceback
import gconf
from i18n import _, N_

GCONF_PLUGINVIEWS = '/apps/accerciser/pluginviews'

PLUGIN_NOTEBOOK_GROUP = 1

class PluginView(gtk.Notebook):
  __gsignals__ = {'plugin_drag_end' : 
                  (gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, 
                   (gobject.TYPE_OBJECT,)),
                  'tab_popup_menu' : 	 
                  (gobject.SIGNAL_RUN_FIRST, 	 
                   gobject.TYPE_NONE, 	 
                   (gobject.TYPE_PYOBJECT, 	 
                    gobject.TYPE_OBJECT))}
  TARGET_PLUGINVIEW = 0
  TARGET_ROOTWIN = 1

  def __init__(self, view_name):
    gtk.Notebook.__init__(self)
    self.view_name = view_name
    self.set_scrollable(True)
    self.set_group_id(PLUGIN_NOTEBOOK_GROUP)
    self.connect('drag_end', self._onDragEnd)
    self.connect('drag_data_get', self._onDragDataGet)
    self.connect('key-press-event', self._onKeyPress)
    self.connect('button-press-event', self._onButtonPress)
    self.dest_type = None
    
  def _onButtonPress(self, nb, event):
    plugin = self._getClickedPlugin(event.x_root, event.y_root)
    if plugin and event.button == 3:
      self.emit('tab_popup_menu', event, plugin)

  def _onKeyPress(self, nb, event):
    if event.keyval == gtk.keysyms.Menu and \
          self.get_property('has-focus'):
      page_num = self.get_current_page()
      child = self.get_nth_page(page_num)
      if isinstance(child, Plugin):
        self.emit('tab_popup_menu', event, self.get_nth_page(page_num))

  def _getClickedPlugin(self, event_x, event_y):
    for child in self.getPlugins():
      tab = self.get_tab_label(child)
      if tab != None and tab.flags() & gtk.MAPPED:
        x, y, w, h = self.getTabAlloc(tab)
        if event_x >= x and \
              event_x <= x + w and \
              event_y >= y and \
              event_y <= y + h:
          return child
    return None

  def getTabAlloc(self, widget):
    gdk_window = widget.window
    origin_x, origin_y = gdk_window.get_origin()
    x, y, width, height = widget.get_allocation()
    if widget.flags() & gtk.NO_WINDOW:
      origin_x += x
      origin_y += y
    return origin_x, origin_y, width, height

  def _onDragDataGet(self, widget, context, selection_data, info, time):
    self.dest_type = info
    selection_data.set(selection_data.target, 8, '')

  def _onDragEnd(self, widget, drag_context):
    if self.dest_type == self.TARGET_PLUGINVIEW:
      return
    index = self.get_current_page()
    child = self.get_nth_page(index)
    self.emit('plugin_drag_end', child)

  def getPlugins(self):
    return filter(lambda x: isinstance(x, Plugin), self.get_children())

  def insert_page(self, child, tab_label=None, position=-1):
    if position == 0 and  \
          isinstance(self.get_nth_page(0), MessageManager.MessageTab):
      position = 1
    if tab_label:
      name = tab_label
    elif isinstance(child, Plugin):
      name = getattr(child,'plugin_name_localized', None) or child.plugin_name
    elif child.name:
      name = child.name
    gtk.Notebook.insert_page(self, child, gtk.Label(name), position=position)
    make_movable = not isinstance(child, MessageManager.MessageTab)
    self.set_tab_detachable(child, make_movable)
    self.set_tab_reorderable(child, make_movable)

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
    self.plugin_view.connect_after('page_removed', self._onPluginRemoved)
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

class ViewManager(gtk.ListStore, Tools):
  COL_NAME = 0
  COL_INSTANCE = 1
  def __init__(self, *main_views):
    if len(main_views) == 0:
      raise TypeError('ViewManager needs at least one main view')
    gtk.ListStore.__init__(self, str, object)
    self.main_views = main_views
    self.main_view = main_views[0]
    for view in self.main_views:
      self.append([view.view_name, view])
      self._connectSignals(view)
    self._ignore_insertion = []
    self._placement_cache = {}
    self._closed = False

  def close(self):
    self._closed = True

  def getViewNameForPlugin(self, plugin_name):
    plugin_layouts = self._StoredViewsLayout()
    for view_name in plugin_layouts:
      if plugin_name in plugin_layouts[view_name]:
        return view_name
    return self.main_view.view_name

  def _getViewByName(self, view_name):
    for row in self:
      if row[self.COL_NAME] == view_name:
        return row[self.COL_INSTANCE]
    return None

  def _onPluginDragEnd(self, view, child):
    new_view = self._newView()
    view.remove(child)
    new_view.append_page(child)

  def _newView(self, view_name=None):
    if not view_name:
      view_name = _('Plugin View')
      view_num = 2
      while view_name in self._getViewNames():
        view_name = _('Plugin View (%d)') % view_num
        view_num += 1
    w = PluginViewWindow(view_name)
    view = w.plugin_view
    self._connectSignals(view)
    self.append([view.view_name, view])
    return view

  def _getViewOrNewView(self, view_name):
    view = self._getViewByName(view_name) or self._newView(view_name)
    return view

  def _onViewDelete(self, view_window, event):
    view = view_window.plugin_view
    for child in view.getPlugins():
      view.remove(child)
      self.main_view.append_page(child)
    self._removeView(view)

  def _removeView(self, view):
    if view in self.main_views:
      return
    iter = self.get_iter_first()
    while iter:
      if self[iter][self.COL_INSTANCE] == view:
        if not self.remove(iter): break
      else:
        iter = self.iter_next(iter)

  def _onTabPopupMenu(self, view, event, plugin): 	 
    menu = self.Menu(plugin, view.get_toplevel())
    if hasattr(event, 'button'):
      menu.popup(None, None, None, event.button, event.time)
    else:
      tab = view.get_tab_label(plugin)
      x, y, w, h = view.getTabAlloc(tab)
      rect = gtk.gdk.Rectangle(x, y, w, h)
      menu.popup(None, None, 
                 lambda m, r: (r.x+r.width/2, r.y+r.height/2, True), 
                 0, event.time, rect)
  
  def _connectSignals(self, view):
    if isinstance(view.parent, PluginViewWindow):
      view.parent.connect('delete_event', self._onViewDelete)
    view.connect('plugin_drag_end', self._onPluginDragEnd)
    view.connect('tab_popup_menu', self._onTabPopupMenu)
    view.connect('page_added', self._onViewLayoutChanged, 'added')
    view.connect('page_removed', self._onViewLayoutChanged, 'removed')
    view.connect('page_reordered', self._onViewLayoutChanged, 'reordered')

  def _onViewLayoutChanged(self, view, plugin, page_num, action):
    if self._closed or not isinstance(plugin, Plugin): return
    if (view.view_name, plugin.plugin_name) in self._ignore_insertion:
      self._ignore_insertion.remove((view.view_name, plugin.plugin_name))
      return
    if self._placement_cache.has_key(plugin.plugin_name):
      self._placement_cache.pop(plugin.plugin_name)
    plugin_layouts = self._StoredViewsLayout()
    try:
      plugin_layout = plugin_layouts[view.view_name]
    except KeyError:
      plugin_layouts[view.view_name] = []
      plugin_layout = plugin_layouts[view.view_name]
    if plugin.plugin_name in plugin_layout:
        plugin_layout.remove(plugin.plugin_name)
    if action in ('reordered', 'added'):
      plugin_layout.insert(page_num, plugin.plugin_name)
    elif action == 'removed':
      self._placement_cache[plugin.plugin_name] = (view.view_name, page_num)
    if len(plugin_layout) == 0:
      self._removeView(view)

  def giveElementFocus(self, element):
    if not getattr(element, 'parent', None):
      return
    view = element.parent
    page_num = view.page_num(element)
    view.set_current_page(page_num)
    view.set_focus_child(element)

  def _onMessageTabShow(self, message_tab):
    self.giveElementFocus(message_tab)

  def addElement(self, element):
    if isinstance(element, Plugin):
      self._addPlugin(element)
    elif isinstance(element, MessageManager.MessageTab):
      element.connect('show', self._onMessageTabShow)
      element.hide()
      self.main_view.insert_page(element, 0)

  def _addPlugin(self, plugin):
    if self._placement_cache.has_key(plugin.plugin_name):
      view_name, position = self._placement_cache.pop(plugin.plugin_name)
      view = self._getViewOrNewView(view_name)
      view.insert_page(plugin, position=position)
    else:
      view_name = self.getViewNameForPlugin(plugin.plugin_name)
      view = self._getViewOrNewView(view_name)
      plugin_layouts = self._StoredViewsLayout()
      plugin_layout = plugin_layouts[view.view_name]
      index = -1
      if plugin.plugin_name in plugin_layout:
        # The plugins that have a higher index.
        successive = plugin_layout[plugin_layout.index(plugin.plugin_name)+1:]
        for child_index, preceding_plugin in enumerate(view.getPlugins()):
          if preceding_plugin.plugin_name in successive:
            # Place new plugin just before the first successive plugin.
            index = child_index
            break
      self._ignore_insertion.append((view.view_name, plugin.plugin_name))
      view.insert_page(plugin, position=index)
    plugin.show_all()

  def initialView(self):
    for view in self._getViews():
      view.set_current_page(0)

  def _getViews(self):
    return [row[self.COL_INSTANCE] for row in self]
  
  def _getViewNames(self):
    return [row[self.COL_NAME] for row in self]

  def changeView(self, plugin, new_view_name):
    if not plugin: return
    old_view = plugin.parent
    new_view = self._getViewOrNewView(new_view_name)
    if old_view is not new_view:
      old_view.remove(plugin)
      new_view.append_page(plugin)

  def Menu(self, context_plugin, transient_window):
    return self._Menu(self, context_plugin, transient_window)

  class _Menu(gtk.Menu):
    RADIO_GROUP = 13
    def __init__(self, view_manager, context_plugin, transient_window):
      gtk.Menu.__init__(self)
      self.view_manager = view_manager
      self._buildMenu(context_plugin, transient_window)

    def _buildMenu(self, context_plugin, transient_window):
      menu_item = None
      for view_name, view in self.view_manager:
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
      self.view_manager.changeView(context_plugin, view.view_name)

    def _onItemActivated(self, menu_item, context_plugin, transient_window):
      new_view_dialog = \
          self._NewViewDialog(self.view_manager, transient_window)
      response_id = new_view_dialog.run()
      plugin_name = new_view_dialog.getEntryText()
      if response_id == gtk.RESPONSE_OK and plugin_name:
        self.view_manager.changeView(context_plugin, plugin_name)
      new_view_dialog.destroy()

    class _NewViewDialog(gtk.Dialog):
      def __init__(self, view_manager, transient_window):
        self.view_manager = view_manager
        gtk.Dialog.__init__(self, _('New View...'), transient_window)
        self.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK,
                         gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        self.set_default_response(gtk.RESPONSE_OK)
        completion = gtk.EntryCompletion()
        completion.set_model(self.view_manager)
        completion.set_text_column(self.view_manager.COL_NAME)
        self.entry = gtk.Entry()
        self.entry.set_completion(completion)
        self.entry.connect('activate', self._onEntryActivate)
        self.vbox.add(self.entry)
        self.entry.show()

      def getEntryText(self):
        return self.entry.get_text()

      def _onEntryActivate(self, entry):
        self.response(gtk.RESPONSE_OK)

  class _StoredViewsLayout(object):
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
