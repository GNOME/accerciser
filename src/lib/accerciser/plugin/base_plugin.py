'''
Defines the base classes for all plugins.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2006, 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import gi

from gi.repository import Gtk as gtk
from accerciser.tools import ToolsAccessor
import traceback

class Plugin(ToolsAccessor):
  '''
  Base class for all plugins. It contains abstract methods for initializing
  and finalizing a plugin. It also holds a reference to the main L{Node} and
  listens for 'accessible_changed' events on it.

  @cvar plugin_name: Plugin name.
  @type plugin_name: string
  @cvar plugin_name_localized: Translated plugin name.
  @type plugin_name_localized: string
  @cvar plugin_description: Plugin description.
  @type plugin_description: string
  @cvar plugin_desc_localized: Translated plugin description.
  @type plugin_desc_localized: string

  @ivar global_hotkeys: A list of tuples containing hotkeys and callbacks.
  @type global_hotkeys: list
  @ivar node: An object with a reference to the currently selected
  accessible in the main  treeview.
  @type node: L{Node}
  @ivar acc: The curently selected accessible in the main treeview.
  @type acc: L{Accessibility.Accessible}
  @ivar _handler: The handler id for the L{Node}'s 'accessible_changed' signal
  @type _handler: integer
  '''
  plugin_name = None
  plugin_name_localized = None
  plugin_description = None
  plugin_desc_localized = None
  def __init__(self, node, message_manager):
    '''
    Connects the L{Node}'s 'accessible_changed' signal to a handler.

    @param node: The applications main L{Node}
    @type node: L{Node}
    @note: L{Plugin} writers should override L{init} to do initialization, not
    this method.
    '''
    self._message_manager = message_manager
    self.global_hotkeys = []
    self.node = node
    self._handler = self.node.connect('accessible_changed', self._onAccChanged)
    self.acc = self.node.acc

  def init(self):
    '''
    An abstract initialization method. Should be overridden by
    L{Plugin} authors.
    '''
    pass

  def _close(self):
    '''
    Called by the L{PluginManager} when a plugin needs to be finalized. This
    method disconnects all signal handlers, and calls L{close} for
    plugin-specific cleanup
    '''
    self.node.disconnect(self._handler)
    self.close()

  def close(self):
    '''
    An abstract initialization method. Should be overridden by
    L{Plugin} authors.
    '''
    pass

  def _onAccChanged(self, node, acc):
    '''
    A signal handler for L{Node}'s 'accessible_changed'. It assigns the
    currently selected accessible to L{acc}, and calls {onAccChanged} for
    plugin-specific event handling.

    @param node: Node that emitted the signal.
    @type node: L{Node}
    @param acc: The new accessibility object.
    @type acc: Accessibility.Accessible
    '''
    if not self.isMyApp(acc):
      self.acc = acc
      self.onAccChanged(acc)

  def onAccChanged(self, acc):
    '''
    An abstract event handler method that is called when the selected
    accessible in the main app changes. Should be overridden by
    L{Plugin} authors.

    @param acc: The new accessibility object.
    @type acc: Accessibility.Accessible
    '''
    pass

  class _PluginMethodWrapper(object):
    '''
    Wraps all callable plugin attributes so that a nice message is displayed
    if an exception is raised.
    '''
    def __init__(self, func):
      '''
      Initialize wrapper.

      @param func: Callable to wrap.
      @type func: callable
      '''
      self.func = func
    def __call__(self, *args, **kwargs):
      '''
      Involed when instance is called. Mimics the wrapped function.

      @param args: Arguments in call.
      @type args: list
      @param kwargs: Key word arguments in call.
      @type kwargs: dictionary

      @return: Any value that is expected from the method
      @rtype: object
      '''
      try:
        return self.func(*args, **kwargs)
      except Exception as e:
        if hasattr(self.func, 'im_self') and hasattr(self.func, 'im_class'):
          message_manager = getattr(self.func.__self__, '_message_manager', None)
          if not message_manager:
            raise e
          message_manager.newPluginError(
            self.func.__self__, self.func.__self__.__class__,
            traceback.format_exception_only(e.__class__, e)[0].strip(),
            traceback.format_exc())

    def __eq__(self, other):
      '''
      Compare the held function and instance with that held by another wrapper.

      @param other: Another wrapper object
      @type other: L{_PluginMethodWrapper}

      @return: Whether this func/inst pair is equal to the one in the other
      wrapper object or not
      @rtype: boolean
      '''
      try:
        return self.func == other.func
      except Exception:
        return False

    def __hash__(self):
      return hash(self.func)




class ViewportPlugin(Plugin, gtk.ScrolledWindow):
  '''
  A base class for plugins that need to represent a GUI to the user.

  @ivar viewport: The top viewport of this plugin.
  @type viewport: gtk.Viewport
  @ivar message_area: Area for plugin messages, mostly errors.
  @type message_area: gtk.Box
  @ivar plugin_area: Main frame where plugin resides.
  @type plugin_area: gtk.Frame
  '''
  def __init__(self, node, message_manager):
    '''
    Initialize object.

    @param node: Main application selected accessible node.
    @type node: L{Node}
    '''
    Plugin.__init__(self, node, message_manager)
    gtk.ScrolledWindow.__init__(self)

    self.set_policy(gtk.PolicyType.AUTOMATIC,
                    gtk.PolicyType.AUTOMATIC)
    self.set_border_width(3)
    self.set_shadow_type(gtk.ShadowType.NONE)
    self.viewport = gtk.Viewport()
    vbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)
    self.viewport.add(vbox)
    self.viewport.connect('set-focus-child', self._onScrollToFocus)
    self.add(self.viewport)
    # Message area
    self.message_area = gtk.Box(orientation=gtk.Orientation.VERTICAL)
    vbox.pack_start(self.message_area, False, False, 0)

    # Plugin area
    self.plugin_area = gtk.Frame()
    self.plugin_area.set_shadow_type(gtk.ShadowType.NONE)
    vbox.pack_start(self.plugin_area, True, True, 0)

  def _onScrollToFocus(self, container, widget):
    '''
    Scrolls a focused child widget in viewport into view.

    @param container: Viewport with child focus change.
    @type container: gtk.Viewport
    @param widget: Child widget of container that had a focus change.
    @type widget: gtk.Widget
    '''
    if widget is None: return
    child = widget
    while isinstance(child, gtk.Container) and \
          child.get_focus_child() is not None:
      child = child.get_focus_child()

    x, y = child.translate_coordinates(self.viewport, 0, 0)
    w, h = child.get_allocation().width, child.get_allocation().height
    vw, vh = self.viewport.get_allocation().width, self.viewport.get_allocation().height

    adj = self.viewport.get_vadjustment()
    if y+h > vh:
      value = adj.get_value() + min((y+h) - vh + 2, y)
      adj.set_value(value)
    elif y < 0:
      adj.set_value(max(adj.get_value() + y - 2, adj.get_lower()))

  def _onMessageResponse(self, error_message, response_id):
    '''
    Standard response callback for error messages.

    @param error_message: Message that emitted this response.
    @type error_message: L{PluginErrorMessage}
    @param response_id: response ID
    @type response_id: integer
    '''
    if response_id == gtk.ResponseType.APPLY:
      pass
    elif response_id == gtk.ResponseType.CLOSE:
      error_message.destroy()

class ConsolePlugin(ViewportPlugin):
  '''
  A base class for plugins that provides a simple console view where textual
  information could be displayed to the user.
  '''

  def __init__(self, node, message_manager):
    '''
    Sets a few predefined settings for the derivative L{gtk.TextView}.

    @param node: Application's main accessibility selection.
    @type node: L{Node}
    '''
    ViewportPlugin.__init__(self, node, message_manager)
    self.text_view = gtk.TextView()
    self.text_view.set_editable(False)
    self.text_view.set_cursor_visible(False)
    self.plugin_area.add(self.text_view)
    text_buffer = self.text_view.get_buffer()
    self.mark = text_buffer.create_mark('scroll_mark',
                                        text_buffer.get_end_iter(),
                                        False)

  def appendText(self, text):
    '''
    Appends the given text to the L{gtk.TextView} which in turn displays the
    text in the plugins's console.

    @param text: Text to append.
    @type text: string
    '''
    text_buffer = self.text_view.get_buffer()
    text_buffer.insert(text_buffer.get_end_iter(), text)
    self.text_view.scroll_mark_onscreen(self.mark)

