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
from gi.repository import Gio as gio
from gi.repository import GLib as glib
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository.Gio import Settings as GSettings
from gi.repository import GObject

from .base_plugin import Plugin
from accerciser.tools import *
from .message import MessageManager
import os
import sys
from accerciser.i18n import _, N_
import gc
from accerciser import menus


GSCHEMA = 'org.a11y.Accerciser'
PLUGVIEWS_GSCHEMA = 'org.a11y.Accerciser.pluginviews'
NEWPLUGVIEWS_GSCHEMA = 'org.a11y.Accerciser.newpluginviews'
NEWPLUGVIEWS_PATH = '/org/a11y/accerciser/newpluginviews/'


class PluginView(gtk.Notebook):
  '''
  Container for multiple plugins. Implemented with a gtk notebook.

  @cvar TARGET_PLUGINVIEW: Drag and drop target ID for another pluginview.
  @type TARGET_PLUGINVIEW: integer
  @cvar TARGET_ROOTWIN: Drag and drop target ID for root window.
  @type TARGET_ROOTWIN: integer
  @ivar NOTEBOOK_GROUP: Group ID for detachable tabs.
  @type NOTEBOOK_GROUP: string

  @ivar view_name: Name of view.
  @type view_name: string
  '''

  __gsignals__ = {'plugin_drag_end' :
                  (GObject.SignalFlags.RUN_FIRST,
                   None,
                   (GObject.TYPE_OBJECT,)),
                  'tab_popup_menu' :
                  (GObject.SignalFlags.RUN_FIRST,
                   None,
                   (GObject.TYPE_PYOBJECT,
                    GObject.TYPE_OBJECT))}
  TARGET_PLUGINVIEW = 0
  TARGET_ROOTWIN = 1
  NOTEBOOK_GROUP = 'NOTEBOOK_GROUP'

  def __init__(self, view_name):
    '''
    Initialize a new plugin view.

    @param view_name: The name of the view.
    @type view_name: string
    '''
    gtk.Notebook.__init__(self)
    self.view_name = view_name
    self.set_scrollable(True)
    self.set_group_name(self.NOTEBOOK_GROUP)
    self.connect('drag-end', self._onDragEnd)
    self.connect('drag-data-get', self._onDragDataGet)
    self.connect('key-press-event', self._onKeyPress)
    self.connect('button-press-event', self._onButtonPress)

    self.dest_type = None

  def _onButtonPress(self, nb, event):
    '''
    Callback for button presses, used for tab context menus.

    @param nb: Notebook that emitted signal.
    @type nb: gtk.Notebook
    @param event: Event object.
    @type event: gtk.dk.Event
    '''
    plugin = self._getClickedPlugin(event.x_root, event.y_root)
    if plugin and event.button == 3:
      self.emit('tab_popup_menu', event, plugin)

  def _onKeyPress(self, nb, event):
    '''
    Callback for key presses, used for tab context menus.

    @param nb: Notebook that emitted signal.
    @type nb: gtk.Notebook
    @param event: Event object.
    @type event: gtk.dk.Event
    '''
    if event.keyval == gdk.KEY_Menu and \
          self.get_property('has-focus'):
      page_num = self.get_current_page()
      child = self.get_nth_page(page_num)
      if isinstance(child, Plugin):
        self.emit('tab_popup_menu', event, self.get_nth_page(page_num))

  def _getClickedPlugin(self, event_x, event_y):
    '''
    Determines which plugin's tab was clicked with given coordinates.

    @param event_x: X coordnate of click.
    @type event_x: integer
    @param event_y: Y coordnate of click.
    @type event_y: integer

    @return: Tab's plugin or None if nothing found.
    @rtype: L{Plugin}
    '''
    for child in self.getPlugins():
      tab = self.get_tab_label(child)
      # TODO-JH: Don't really know if this is correct
      if tab != None and tab.get_state_flags() & tab.get_mapped():
        x, y, w, h = self.getTabAlloc(tab)
        if event_x >= x and \
              event_x <= x + w and \
              event_y >= y and \
              event_y <= y + h:
          return child
    return None

  def getTabAlloc(self, widget):
    '''
    Get the screen allocation of the given tab.

    @param widget: The tab widget.
    @type widget: gtk.Widget

    @return: X, Y, width any height coordinates.
    @rtype: tuple
    '''
    gdk_window = widget.get_window()
    origin_z, origin_x, origin_y = gdk_window.get_origin()
    alloc = widget.get_allocation()
    x, y, width, height = \
        alloc.x, alloc.y, alloc.width, alloc.height
    # TODO-JH: Review this conversion
    has_window = not(widget.get_has_window())
    if bool(widget.get_state_flags().value_names) & has_window:
      origin_x += x
      origin_y += y
    return origin_x, origin_y, width, height

  def _onDragDataGet(self, widget, context, selection_data, info, time):
    '''
    Data transfer function for drag and drop.

    @param widget: Widget that recieved the signal.
    @type widget: gtk.Widget
    @param context: Drag context for this operation
    @type context: gtk.gdk.DragContext
    @param selection_data: A selection data object
    @type selection_data: gtk.SelectionData
    @param info: An ID of the drag
    @type info: integer
    @param time: The timestamp of the drag event.
    @type time: float
    '''
    self.dest_type = info
    selection_data.set(selection_data.get_target(), 8, '')

  def _onDragEnd(self, widget, drag_context):
    '''
    Callback for completed drag operation.

    @param widget: Widget that recieved the signal.
    @type widget: gtk.Widget
    @param drag_context: Drag context for this operation
    @type drag_context: gtk.gdk.DragContext
    '''
    if self.dest_type == self.TARGET_PLUGINVIEW:
      return
    index = self.get_current_page()
    child = self.get_nth_page(index)
    self.emit('plugin_drag_end', child)

  def getPlugins(self):
    '''
    Return list of plugins in given view. Filter out tabs that are not plugins.

    @return: Plugins in given view.
    @rtype: List of {Plugin}
    '''
    return [x for x in self.get_children() if isinstance(x, Plugin)]

  def insert_page(self, child, tab_label=None, position=-1):
    '''
    Override gtk.Notebook's method. Use the plugin's name or widget's name
    as default tab label. Keep message tab as first tab.

    @param child: Child widget to insert.
    @type child: gtk.Widget
    @param tab_label: Label to use. Plugin name will be used by default.
    @type tab_label: gtk.Widget
    @param position: Position to insert child.
    @type position: integer
    '''
    if position != -1 and  \
          isinstance(self.get_nth_page(0), MessageManager.MessageTab):
      position += 1
    if tab_label:
      name = tab_label
    elif isinstance(child, Plugin):
      name = getattr(child, 'plugin_name_localized', None) or child.plugin_name
    elif child.get_name():
      name = child.get_name()
    gtk.Notebook.append_page(self, child, None)
    gtk.Notebook.reorder_child(self, child, position)
    gtk.Notebook.set_tab_label(self, child, gtk.Label.new(name))

  def append_page(self, child, tab_label=None):
    '''
    Override gtk.Notebook's method. Use the plugin's name or widget's name
    as default tab label. Keep message tab as first tab.

    @param child: Child widget to insert.
    @type child: gtk.Widget
    @param tab_label: Label to use. Plugin name will be used by default.
    @type tab_label: gtk.Widget
    '''
    self.insert_page(child, tab_label, -1)

  def prepend_page(self, child, tab_label=None):
    '''
    Override gtk.Notebook's method. Use the plugin's name or widget's name
    as default tab label. Keep message tab as first tab.

    @param child: Child widget to insert.
    @type child: gtk.Widget
    @param tab_label: Label to use. Plugin name will be used by default.
    @type tab_label: gtk.Widget
    '''
    self.insert_page(child, tab_label, 0)

  def focusTab(self, tab_num):
    '''
    Set focus on given tab number.

    @param tab_num: Index within visible tabs.
    @type tab_num: integer
    '''
    children = self.get_children()
    shown_children = [x for x in children if x.get_property('visible')]
    try:
      child = shown_children[tab_num]
    except IndexError:
      return
    self.set_current_page(children.index(child))
    self.grab_focus()

  def getNVisiblePages(self):
    '''
    Get number of visible children.

    @return: Number of visible children.
    @rtype: integer
    '''
    shown_children = [x for x in self.get_children() if x.get_property('visible')]
    return len(shown_children)

class PluginViewWindow(gtk.Window, ToolsAccessor):
  '''
  Standalone window with a plugin view.

  @ivar plugin_view: Embedded plugin view.
  @type plugin_view: L{PluginView}
  '''
  def __init__(self, view_name):
    '''
    Initialize a new plugin view window.

    @param view_name: The name of the view.
    @type view_name: string
    '''
    gtk.Window.__init__(self)
    self.plugin_view = PluginView(view_name)
    self.add(self.plugin_view)

    gspath = NEWPLUGVIEWS_PATH + view_name.lower().replace(' ', '-') + '/'
    gsettings = GSettings.new_with_path(NEWPLUGVIEWS_GSCHEMA, gspath)
    width = gsettings.get_int('width')
    height = gsettings.get_int('height')
    self.set_default_size(width, height)
    self.connect('key_press_event', self._onKeyPress)
    self.plugin_view.connect_after('page_removed', self._onPluginRemoved)
    self.set_title(view_name)
    self.set_position(gtk.WindowPosition.MOUSE)
    self.show_all()
    self.connect('size-allocate', self._onResize)

  def _onResize(self, widget, allocation):
    '''
    Callback for window resizing. Used for persisting view sizes across
    sessions.

    @param widget: Window widget.
    @type widget: gtk.Widget
    @param allocation: The new allocation.
    @type allocation: gtk.gdk.Rectangle
    '''
    view_name = self.plugin_view.view_name
    gspath = NEWPLUGVIEWS_PATH + view_name.lower().replace(' ', '-') + '/'
    gsettings = GSettings.new_with_path(NEWPLUGVIEWS_GSCHEMA, gspath)
    gsettings.set_int('width', self.get_allocated_width())
    gsettings.set_int('height', self.get_allocated_height())

  def _onPluginRemoved(self, pluginview, page, page_num):
    '''
    Callback for removed tabs. If there are no plugins in a stand alone view,
    destroy it.

    @param pluginview: Plugin view that emitted signal.
    @type pluginview: L{PluginView}
    @param page: Child that has been removed.
    @type page: gtk.Widget
    @param page_num: Tab index of child.
    @type page_num: integer
    '''
    if pluginview.get_n_pages() == 0:
      self.destroy()

  def _onKeyPress(self, widget, event):
    '''
    Callback for keypresses in window. Enables alt-<num> tab switching.

    @param widget: Window widget.
    @type widget: gtk.Widget
    @param event: Event object
    @type event: gtk.gdk.Event
    '''
    if event.state & gdk.ModifierType.MOD1_MASK and \
          event.keyval in range(gdk.keyval_from_name('0'),
                                 gdk.keyval_from_name('9')):
      tab_num = event.keyval - gdk.keyval_from_name('0') or 10
      pages_count = self.plugin_view.get_n_pages()
      if pages_count >= tab_num:
        self.plugin_view.focusTab(tab_num - 1)


class ViewManager(object):
  '''
  Manage plugins and their views.
  '''
  def __init__(self, application, *perm_views):
    '''
    Initialize view manager.

    @param application: The application.
    @type application: gtk.Application.
    @param perm_views: List of permanent views, at least one is required.
    @type perm_views: list of {PluginView}
    '''
    self.application = application
    self._perm_views = perm_views
    gsettings = GSettings.new(PLUGVIEWS_GSCHEMA)
    single = gsettings.get_boolean('layout-single')
    self._initViewModel(single)
    self._setupActions()

  def _setupActions(self):
    '''
    Sets up actions related to plugin layout.
    '''
    single = isinstance(self._view_model, SingleViewModel)
    menu, name, label, accel, callback = (menus.view_menu_general_section, 'single_view_mode', \
                                         _('_Single plugins view'), '<Control>t', self._onSingleViewToggled)
    action_name = 'app.' + name
    menu_item = gio.MenuItem.new(label, action_name)
    menu.append_item(menu_item)
    action = gio.SimpleAction.new_stateful(name, None, glib.Variant.new_boolean(single))
    action.connect('change-state', callback)
    self.application.set_accels_for_action(action_name, [accel])
    self.application.add_action(action)

    self.setSingleMode(action.get_property('state').get_boolean())


  def _onSingleViewToggled(self, action, value, data=None):
    '''
    Callback for single view toggle action.

    @param action: Action object that emitted callback.
    @type action: gio.SimpleAction
    '''
    action.set_state(value)
    self.setSingleMode(value.get_boolean())

  def setSingleMode(self, single):
    '''
    Toggle single mode on or off.

    @param single: True if we want single mode.
    @type single: boolean
    '''
    if isinstance(self._view_model, SingleViewModel) == single:
      return
    gsettings = GSettings.new(PLUGVIEWS_GSCHEMA)
    gsettings.set_boolean('layout-single', single)
    plugins = self._view_model.getViewedPlugins()
    self._view_model.close()
    del self._view_model
    for plugin in plugins:
      if plugin.get_parent():
        plugin.get_parent().remove(plugin)
    self._initViewModel(single)
    for plugin in plugins:
      self._view_model.addElement(plugin)

  def _initViewModel(self, single):
    '''
    Initialize a view model, either multi view or single view.

    @param single: True if we want single mode.
    @type single: boolean
    '''
    if single:
      self._view_model = SingleViewModel(*self._perm_views)
    else:
      self._view_model = MultiViewModel(*self._perm_views)

  def addElement(self, element):
    '''
    Add an element to a plugin view.

    @param element: The element to be added to a view.
    @type element: gtk.Widget
    '''
    self._view_model.addElement(element)

  def close(self):
    '''
    Do cleanup.
    '''
    self._view_model.close()

  def initialView(self):
    '''
    Do something when view/s are first displayed.
    '''
    self._view_model.initialView()

  def giveElementFocus(self, element):
    '''
    Give focus to given element (ie. a plugin)

    @param element: The element to give focus to.
    @type element: gtk.Widget
    '''
    self._view_model.giveElementFocus(element)

  def changeView(self, plugin, new_view_name):
    '''
    Put a plugin instance in a different view.

    @param plugin: Plugin to move.
    @type plugin: L{Plugin}
    @param new_view_name: New view name.
    @type new_view_name: string
    '''
    self._view_model.changeView(plugin, new_view_name)

  def getViewNameForPlugin(self, plugin_name):
    '''
    Get the view name for a given plugin name.

    @param plugin_name: Plugin's name to lookup view for.
    @type plugin_name: string

    @return: View name for plugin.
    @rtype: string
    '''
    return self._view_model.getViewNameForPlugin(plugin_name)

  def Menu(self, context_plugin, transient_window):
    '''
    Return a context menu for the given plugin with view manipulation options.

    @param context_plugin: Subject plugin of this menu.
    @type context_plugin: L{Plugin}
    @param transient_window: Transient parent window. Used for keeping the
    new view dialog modal.
    @type transient_window: gtk.Window

    @return: A Menu widget
    @rtype: gtk.Menu
    '''
    return self._view_model.Menu(context_plugin, transient_window)

class BaseViewModel(ToolsAccessor):
  '''
  Base class for views model

  @ivar perm_views: List of permanent views.
  @type perm_views: list of L{PluginView}
  @ivar main_view: Main view.
  @type main_view: L{PluginView}
  '''
  def __init__(self, *perm_views):
    '''
    Initialize view model.

    @param perm_views: List of permanent views, at least one is required.
    @type perm_views: list of {PluginView}
    '''
    if len(perm_views) == 0:
      raise TypeError('View model needs at least one permanent view')
    self.perm_views = perm_views
    self.main_view = perm_views[0]

  def addElement(self, element):
    '''
    Add an element to a plugin view. If the element is a message tab, put it as
    the first tab in the main view. If the element is a plugin, check if it's
    placement is cached in this instance or read it's position from gsettings.
    By default a plugin is appended to the main view.

    @param element: The element to be added to a view.
    @type element: gtk.Widget
    '''
    if isinstance(element, Plugin):
      self.addPlugin(element)
    elif isinstance(element, MessageManager.MessageTab):
      element.connect('show', Proxy(self._onMessageTabShow))
      element.hide()
      self.main_view.insert_page(element, 0)
      self.main_view.set_tab_detachable(element, False)
      self.main_view.set_tab_reorderable(element, False)

  def addPlugin(self, plugin):
    '''
    Add a plugin to the view. Check if it's placement is cached in this
    instance or read it's position from gsettings. By default a plugin is
    appended to the main view.

    @param plugin: Plugin to add.
    @type plugin: L{Plugin}
    '''
    pass

  def close(self):
    '''
    Do cleanup.
    '''
    pass

  def initialView(self):
    '''
    Do something when view/s are first displayed.
    '''
    pass

  def giveElementFocus(self, element):
    '''
    Give focus to given element (ie. a plugin)

    @param element: The element to give focus to.
    @type element: gtk.Widget
    '''
    if not getattr(element, 'parent', None):
      return
    view = element.parent
    page_num = view.page_num(element)
    view.set_current_page(page_num)
    view.set_focus_child(element)

  def _onMessageTabShow(self, message_tab):
    '''
    Callback for when a message tab appears. Give it focus.

    @param message_tab: Message tab that just appeared.
    @type message_tab: L{MessageManager.MessageTab}
    '''
    self.giveElementFocus(message_tab)

  def changeView(self, plugin, new_view_name):
    '''
    Put a plugin instance in a different view.

    @param plugin: Plugin to move.
    @type plugin: L{Plugin}
    @param new_view_name: New view name.
    @type new_view_name: string
    '''
    pass

  def getViewNameForPlugin(self, plugin_name):
    '''
    Get the view name for a given plugin name.

    @param plugin_name: Plugin's name to lookup view for.
    @type plugin_name: string

    @return: View name for plugin.
    @rtype: string
    '''
    pass

  def getViewedPlugins(self):
    '''
    Get a list of all viewed plugins that are in the managed view/s.
    '''
    pass

  def Menu(self, context_plugin, transient_window):
    '''
    Return a context menu for the given plugin with view manipulation options.

    @param context_plugin: Subject plugin of this menu.
    @type context_plugin: L{Plugin}
    @param transient_window: Transient parent window. Used for keeping the
    new view dialog modal.
    @type transient_window: gtk.Window

    @return: A Menu widget
    @rtype: gtk.Menu
    '''
    return gtk.Menu()

class SingleViewModel(BaseViewModel):
  def addPlugin(self, plugin):
    '''
    Add a given plugin to our single view in alphabetical order.

    @param plugin: Plugin to add
    @type plugin: L{Plugin}
    '''
    plugin_names = \
        [p.plugin_name.lower() for p in self.main_view.getPlugins()]
    plugin_names.append(plugin.plugin_name.lower())
    plugin_names.sort()
    index = plugin_names.index(plugin.plugin_name.lower())
    self.main_view.insert_page(plugin, position=index)
    self.main_view.set_tab_detachable(plugin, False)
    self.main_view.set_tab_reorderable(plugin, False)
    plugin.show_all()
  def initialView(self):
    '''
    Set tab to first tab.
    '''
    self.main_view.set_current_page(0)
  def getViewedPlugins(self):
    '''
    Get all managed plugins.

    @return: list of all managed plugins.
    @rtype: list of PLugin
    '''
    return self.main_view.getPlugins()

class MultiViewModel(list, BaseViewModel):
  '''
  Manages all plugin views. Implements a gtk.ListStore of all views.
  Persists plugin view placements across sessions.

  @cvar COL_NAME: View name column ID.
  @type COL_NAME: integer
  @cvar COL_INSTANCE: View instance column ID.
  @type COL_INSTANCE: integer

  @ivar perm_views: List of permanent views.
  @type perm_views: list of L{PluginView}
  @ivar main_view: Main view.
  @type main_view: L{PluginView}
  @ivar _ignore_insertion: A list of tuples with view and plugin names that
  should be ignored and not go in to gsettings. This is to avoid recursive
  gsettings modification.
  @type _ignore_insertion: list of tuples
  @ivar _placement_cache: A cache of recently disabled plugins with their
  placement. allowsthem to be enabled in to the same position.
  @type _placement_cache: dictionary
  @ivar _closed: Indicator to stop writing plugin remove events to gsettings.
  @type _closed: boolean
  '''
  COL_NAME = 0
  COL_INSTANCE = 1
  def __init__(self, *perm_views):
    '''
    Initialize view manager.

    @param perm_views: List of permanent views, at least one is required.
    @type perm_views: list of {PluginView}
    '''
    BaseViewModel.__init__(self, *perm_views)
    for view in self.perm_views:
      self.append(view)
      self._connectSignals(view)
    self._ignore_insertion = []
    self._placement_cache = {}
    self._closed = False

  def close(self):
    '''
    Stops gsettings maniputaion.
    '''
    self._closed = True

  def getViewNameForPlugin(self, plugin_name):
    '''
    Get the view name for a given plugin name as defined in gsettings.
    Or return name of main view.

    @param plugin_name: Plugin's name to lookup view for.
    @type plugin_name: string

    @return: View name for plugin.
    @rtype: string
    '''
    plugin_layouts = self._getPluginLayouts()
    for view_name in plugin_layouts:
      if plugin_name in plugin_layouts[view_name]:
        return view_name
    return self.main_view.view_name

  def _getViewByName(self, view_name):
    '''
    Return the view instance of the given name.

    @param view_name: Name of view to retrieve.
    @type view_name: string

    @return: View instance or None
    @rtype: L{PluginView}
    '''
    for view in self:
      if view.view_name == view_name:
        return view
    return None

  def _onPluginDragEnd(self, view, plugin):
    '''
    Callback for the end of a drag operation of a plugin. Only is called
    when the drag ends on the root window.

    @param view: Current plugin's view.
    @type view: L{PluginView}
    @param plugin: Plugin that was dragged.
    @type plugin: L{Plugin}
    '''
    new_view = self._newView()
    view.remove(plugin)
    new_view.append_page(plugin)
    new_view.set_tab_detachable(plugin, True)
    new_view.set_tab_reorderable(plugin, True)

  def _newView(self, view_name=None):
    '''
    Creates a new view.

    @param view_name: An optional view name. Gives a more mundane one if no
    name is provided.
    @type view_name: string

    @return: New view
    @rtype: L{PluginView}
    '''
    if not view_name:
      view_name = _('Plugin View')
      view_num = 2
      while view_name in self._getViewNames():
        view_name = _('Plugin View (%d)') % view_num
        view_num += 1
    w = PluginViewWindow(view_name)
    view = w.plugin_view
    self._connectSignals(view)
    self.append(view)
    return view

  def _getViewOrNewView(self, view_name):
    '''
    Get an existing or new view with the current name.

    @param view_name: View's name
    @type view_name: string

    @return: New or existing view.
    @rtype: L{PluginView}
    '''
    view = self._getViewByName(view_name) or self._newView(view_name)
    return view

  def _onViewDelete(self, view_window, event):
    '''
    Callback for a view window's delete event. Puts all orphaned plugins
    in main view.

    @param view_window: View window that emitted delete event.
    @type view_window: L{PluginViewWindow}
    @param event: Event object.
    @type event: gtk.gdk.Event
    '''
    view = view_window.plugin_view
    for child in view.getPlugins():
      view.remove(child)
      self.main_view.append_page(child)
    self._removeView(view)

  def _removeView(self, view):
    '''
    Removes view from model.

    @param view: View to remove.
    @type view: L{PluginView}
    '''
    if view in self.perm_views:
      return
    if view in self:
      self.remove(view)

  def _onTabPopupMenu(self, view, event, plugin):
    '''
    Callback for popup menu signal from plugin view. Displays a context menu
    with available views.

    @param view: Plugin view that emitted this signal.
    @type view: L{PluginView}
    @param event: Relevant event object that will be used in popup menu.
    @type event: gtk.gdk.Event
    @param plugin: Plugin of tab that was clicked or pressed.
    @type plugin: L{Plugin}
    '''
    menu = self.Menu(plugin, view.get_toplevel())
    if hasattr(event, 'button'):
      menu.popup(None, None, None, None, event.button, event.time)
    else:
      tab = view.get_tab_label(plugin)
      x, y, w, h = view.getTabAlloc(tab)
      rect = gdk.Rectangle(x, y, w, h)
      menu.popup(None, None,
                 lambda m, r: (r.x+r.width/2, r.y+r.height/2, True),
                 rect, 0, event.time)

  def _connectSignals(self, view):
    '''
    Convenience function for connecting all needed signal callbacks.

    @param view: Plugin view to connect.
    @type view: :{PluginView}
    '''
    if isinstance(view.get_parent(), PluginViewWindow):
      view.get_parent().connect('delete-event', Proxy(self._onViewDelete))
    view.connect('plugin-drag-end', Proxy(self._onPluginDragEnd))
    view.connect('tab-popup-menu', Proxy(self._onTabPopupMenu))
    view.connect('page-added', Proxy(self._onViewLayoutChanged), 'added')
    view.connect('page-removed', Proxy(self._onViewLayoutChanged), 'removed')
    view.connect('page-reordered', Proxy(self._onViewLayoutChanged), 'reordered')

  def _onViewLayoutChanged(self, view, plugin, page_num, action):
    '''
    Callback for all layout changes. Updates gsettings.

    @param view: View that emitted the signal.
    @type view: L{PluginView}
    @param plugin: Plugin that moved.
    @type plugin: L{Plugin}
    @param page_num: Plugin's position in view.
    @type page_num: integer
    @param action: Action that triggered this event.
    @type action: string
    '''
    if self._closed or not isinstance(plugin, Plugin): return
    if (view.view_name, plugin.plugin_name) in self._ignore_insertion:
      self._ignore_insertion.remove((view.view_name, plugin.plugin_name))
      return
    if plugin.plugin_name in self._placement_cache:
      self._placement_cache.pop(plugin.plugin_name)

    plugin_layouts = self._getPluginLayouts()
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

    self._setPluginLayouts(plugin_layouts)

  def _setPluginLayouts(self, plugin_layouts):
    self.plugviews = GSettings.new(PLUGVIEWS_GSCHEMA)
    self.plugviews.set_strv('top-panel-layout', plugin_layouts.pop('Top panel'))
    self.plugviews.set_strv('bottom-panel-layout', plugin_layouts.pop('Bottom panel'))

    for plugview in list(plugin_layouts.keys()):
      gspath = NEWPLUGVIEWS_PATH + plugview.lower().replace(' ', '-') + '/'
      newview = GSettings.new_with_path(NEWPLUGVIEWS_GSCHEMA, gspath)
      newview.set_strv('layout', plugin_layouts[plugview])
      l = self.plugviews.get_strv('available-newviews')
      l.append(plugview)
      self.plugviews.set_strv('available-newviews', l)

  def _getPluginLayouts(self):
    plugin_layouts= {}
    self.plugviews = GSettings.new(PLUGVIEWS_GSCHEMA)
    plugin_layouts['Top panel'] = self.plugviews.get_strv('top-panel-layout')
    plugin_layouts['Bottom panel'] = self.plugviews.get_strv('bottom-panel-layout')

    for plugview in self.plugviews.get_strv('available-newviews'):
      gspath = NEWPLUGVIEWS_PATH + plugview.lower().replace(' ', '-') + '/'
      newview = GSettings.new_with_path(NEWPLUGVIEWS_GSCHEMA, gspath)
      layout = newview.get_strv('layout')
      if layout:
        plugin_layouts[plugview] = layout
      else:
        l = self.plugviews.get_strv('available-newviews')
        l.remove(plugview)
        self.plugviews.set_strv('available-newviews', l)
    return plugin_layouts


  def addPlugin(self, plugin):
    '''
    Add a plugin to the view. Check if it's placement is cached in this
    instance or read it's position from gsettings. By default a plugin is
    appended to the main view.

    @param plugin: Plugin to add.
    @type plugin: L{Plugin}
    '''
    if plugin.plugin_name in self._placement_cache:
      view_name, index = self._placement_cache.pop(plugin.plugin_name)
      view = self._getViewOrNewView(view_name)
    else:
      view_name = self.getViewNameForPlugin(plugin.plugin_name)
      view = self._getViewOrNewView(view_name)
      plugin_layouts = self._getPluginLayouts()
      try:
        plugin_layout = plugin_layouts[view.view_name]
      except KeyError:
        plugin_layout = []
        plugin_layouts[view.view_name] = plugin_layout
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
      self._setPluginLayouts(plugin_layouts)

    view.insert_page(plugin, position=index)
    view.set_tab_detachable(plugin, True)
    view.set_tab_reorderable(plugin, True)
    plugin.show_all()

  def initialView(self):
    '''
    Set the current tab of all views to be the first one.
    Used when Accercier first starts.
    '''
    for view in self:
      view.set_current_page(0)

  def getViewedPlugins(self):
    '''
    Get all plugins from all views.
    '''
    rv = []
    for view in self:
      rv.extend(view.getPlugins())
    return rv

  def _getViewNames(self):
    '''
    Get a list of all managed view names.

    @return: A list of view names.
    @rtype: list of string
    '''
    return [view.view_name for view in self]

  def changeView(self, plugin, new_view_name):
    '''
    Put a plugin instance in a different view. If given view name does not
    exist, create it.

    @param plugin: Plugin to move.
    @type plugin: L{Plugin}
    @param new_view_name: New view name.
    @type new_view_name: string
    '''
    if not plugin or not isinstance(plugin, gtk.Widget): return
    old_view = plugin.get_parent()
    new_view = self._getViewOrNewView(new_view_name)
    if old_view is not new_view:
      old_view.remove(plugin)
      new_view.append_page(plugin)
      new_view.set_tab_detachable(plugin, True)
      new_view.set_tab_reorderable(plugin, True)

  def Menu(self, context_plugin, transient_window):
    '''
    Helps emulate a non-static inner class. These don't exist in python,
    I think.

    @param context_plugin: Subject plugin of this menu.
    @type context_plugin: L{Plugin}
    @param transient_window: Transient parent window. Used for keeping the
    new view dialog modal.
    @type transient_window: gtk.Window

    @return: An inner menu class.
    @rtype: L{ViewManager._Menu}
    '''
    return self._Menu(self, context_plugin, transient_window)

  class _Menu(gtk.Menu):
    '''
    Implements a popup menu for a plugin that will allow putting the plugin in
    a different view.

    @cvar RADIO_GROUP: Radio menu item's group id.
    @type RADIO_GROUP: integer

    @ivar view_manager: View manager to use as data model and controller.
    @type view_manager: L{ViewManager}
    '''
    RADIO_GROUP = 13
    def __init__(self, view_manager, context_plugin, transient_window):
      '''
      Initialize menu.

      @param view_manager: View manager to use as data model and controller.
      @type view_manager: L{ViewManager}
      @param context_plugin: Subject plugin of this menu.
      @type context_plugin: L{Plugin}
      @param transient_window: Transient parent window. Used for keeping the
      new view dialog modal.
      @type transient_window: gtk.Window
      '''
      gtk.Menu.__init__(self)
      self.view_manager = view_manager
      if isinstance(context_plugin, gtk.Widget):
        self._buildMenu(context_plugin, transient_window)

    def _buildMenu(self, context_plugin, transient_window):
      '''
      Build the menu according to the view managers model.

      @param context_plugin: Subject plugin of this menu.
      @type context_plugin: L{Plugin}
      @param transient_window: Transient parent window. Used for keeping the
      new view dialog modal.
      @type transient_window: gtk.Window
      '''
      menu_item = None
      for view in self.view_manager:
        menu_item = gtk.RadioMenuItem(label = _(view.view_name))
        menu_item.set_name(view.view_name)
        menu_item.connect('toggled', self._onItemToggled, view, context_plugin)
        menu_item.set_active(view == context_plugin.get_parent())
        self.append(menu_item)
        menu_item.show()
      menu_item = gtk.SeparatorMenuItem()
      self.append(menu_item)
      menu_item.show()
      menu_item = gtk.MenuItem(label="<i>" + _('_New view…') + "</i>")
      menu_item.get_child().set_use_markup(True)
      menu_item.connect('activate', self._onItemActivated,
                        context_plugin, transient_window)
      self.append(menu_item)
      menu_item.show()

    def _onItemToggled(self, menu_item, view, context_plugin):
      '''
      Callback for radio item toggles. Change the views accordingly.

      @param menu_item: Menu item that was toggled
      @type menu_item: gtk.RadioMenuItem
      @param view: View that was chosen.
      @type view: L{PluginView}
      @param context_plugin: Subject plugin of this menu.
      @type context_plugin: L{Plugin}
      '''
      self.view_manager.changeView(context_plugin, view.view_name)

    def _onItemActivated(self, menu_item, context_plugin, transient_window):
      '''
      Callback for "new view" menu item. Creates a dialog for
      entering a view name.

      @param menu_item: Menu item that was activated.
      @type menu_item: gtk.MenuItem
      @param context_plugin: Subject plugin of this menu.
      @type context_plugin: L{Plugin}
      @param transient_window: Transient parent window. Used for keeping the
      new view dialog modal.
      @type transient_window: gtk.Window
      '''
      new_view_dialog = \
          self._NewViewDialog(self.view_manager, transient_window)
      response_id = new_view_dialog.run()
      plugin_name = new_view_dialog.getEntryText()
      if response_id == gtk.ResponseType.OK and plugin_name:
        self.view_manager.changeView(context_plugin, plugin_name)
      new_view_dialog.destroy()

    class _NewViewDialog(gtk.Dialog):
      '''
      Small dialog that allows entry of a new view name.
      '''
      def __init__(self, view_manager, transient_window):
        '''


        @param view_manager: View manager to use as data model and controller.
        @type view_manager: L{ViewManager}
        @param transient_window: Transient parent window. Used for keeping the
        new view dialog modal.
        @type transient_window: gtk.Window
        '''
        self.view_manager = view_manager
        gtk.Dialog.__init__(self, _('New View…'), transient_window)
        ok_button = self.add_button(_('_OK'), gtk.ResponseType.OK)
        ok_button.set_image(gtk.Image.new_from_icon_name("gtk-apply", gtk.IconSize.BUTTON))
        close_button = self.add_button(_('_Close'), gtk.ResponseType.CLOSE)
        close_button.set_image(gtk.Image.new_from_icon_name("window-close", gtk.IconSize.BUTTON))
        self.set_default_response(gtk.ResponseType.OK)
        completion = gtk.EntryCompletion()
        complete_model = gtk.ListStore(str)
        for view in self.view_manager:
          complete_model.append([view.view_name])
        completion.set_model(complete_model)
        completion.set_text_column(0)
        self.entry = gtk.Entry()
        self.entry.set_completion(completion)
        self.entry.connect('activate', self._onEntryActivate)
        self.box = self.get_children()[0]
        self.box.add(self.entry)
        self.entry.show()

      def getEntryText(self):
        '''
        Get the contents of the entry widget.

        @return: Text in entry box.
        @rtype: string
        '''
        return self.entry.get_text()

      def _onEntryActivate(self, entry):
        '''
        Callback for activation of the entry box. Return an OK response.

        @param entry: Entry box that was activated.
        @type entry: gtk.Entry
        '''
        self.response(gtk.ResponseType.OK)

