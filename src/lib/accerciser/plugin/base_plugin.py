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

import gtk
from accerciser.tools import Tools
import traceback
import gobject, pango

class Plugin(Tools):
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

  def __getattribute__(self, name):
    '''
    Wraps attributes that are callable in a wrapper. This allows us to 
    catch exceptions and display them in the plugin view if necessary.
    
    @param name: Name of attribure we are seeking.
    @type name: string
    
    @return: Wrap attribut in L{_PluginMethodWrapper} if callable
    @rtype: object
    '''
    obj = super(Plugin, self).__getattribute__(name)
    if callable(obj):
      method_wrapper = \
          super(Plugin, self).__getattribute__('_PluginMethodWrapper')
      return method_wrapper(obj)
    else:
      return obj

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
      except Exception, e:
        if hasattr(self.func, 'im_self') and hasattr(self.func, 'im_class'):
          message_manager = getattr(self.func.im_self, '_message_manager', None)
          if not message_manager:
            raise e
          message_manager.newPluginError(
            self.func.im_self, self.func.im_class,
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
  @type message_area: gtk.VBox
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

    self.set_policy(gtk.POLICY_AUTOMATIC, 
                    gtk.POLICY_AUTOMATIC)
    self.set_border_width(3)
    self.set_shadow_type(gtk.SHADOW_NONE)
    self.viewport = gtk.Viewport()
    vbox = gtk.VBox()
    self.viewport.add(vbox)
    self.add(self.viewport)
    # Message area
    self.message_area = gtk.VBox()
    vbox.pack_start(self.message_area, False, False)

    # Plugin area
    self.plugin_area = gtk.Frame()
    self.plugin_area.set_shadow_type(gtk.SHADOW_NONE)
    vbox.pack_start(self.plugin_area)

  def _onMessageResponse(self, error_message, response_id):
    '''
    Standard response callback for error messages.
    
    @param error_message: Message that emitted this response.
    @type error_message: L{PluginErrorMessage}
    @param response_id: response ID
    @type response_id: integer
    '''
    if response_id == gtk.RESPONSE_APPLY:
      pass
    elif response_id == gtk.RESPONSE_CLOSE:
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

