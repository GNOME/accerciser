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
from tools import Tools, Proxy
import traceback
import gobject, pango

class Plugin(Tools):
  '''
  Base class for all plugins. It contains abstract methods for initializing 
  and finalizing a plugin. It also holds a reference to the main L{Node} and
  listens for 'accessible_changed' events on it.

  @ivar node: An object with a reference to the currently selected 
  accessible in the main  treeview.
  @type node: L{Node}
  @ivar acc: The curently selected accessible in the main treeview.
  @type acc: L{pyLinAcc.Accessible}
  @ivar _handler: The handler id for the L{Node}'s 'accessible_changed' signal
  @type _handler: integer
  '''

  def __init__(self, node):
    '''
    Connects the L{Node}'s 'accessible_changed' signal to a handler.
    
    @param node: The applications main L{Node}
    @type node: L{Node}
    @note: L{Plugin} writers should override L{init} to do initialization, not
    this method.
    '''
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
    current;y selected accessible to L{acc}, and calls {onAccChanged} for
    plugin-specific event handling.
    '''
    self.acc = acc
    self.onAccChanged(acc)

  def onAccChanged(self, acc):
    '''
    An abstract event handler method that is called when the selected 
    accessible in the main app changes. Should be overridden by 
    L{Plugin} authors.
    '''
    pass 
  def __getattribute__(self, name):
    obj = super(Plugin, self).__getattribute__(name)
    if callable(obj):
      return PluginMethodWrapper(obj)
    else:
      return obj

class ViewportPlugin(Plugin, gtk.ScrolledWindow):
  '''
  A base class for plugins that need to represent a GUI to the user.
  '''
  __gsignals__ = {'reload-request' : 
                  (gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, 
                   ())}
  def __init__(self, node):
    gtk.ScrolledWindow.__init__(self)
    Plugin.__init__(self, node)

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
    if response_id == gtk.RESPONSE_APPLY:
      print 'refresh'
      self.emit('reload-request')
    elif response_id == gtk.RESPONSE_CLOSE:
      error_message.destroy()

class ConsolePlugin(ViewportPlugin):
  '''
  A base class for plugins that provides a simple console view where textual 
  information could be displayed to the user.
  '''

  def __init__(self, node):
    '''
    Sets a few predefined settings for the derivative L{gtk.TextView}.
    '''
    ViewportPlugin.__init__(self, node)
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

class PluginMethodWrapper(object):
  def __init__(self, func):
    self.func = func
  def __call__(self, *args, **kwargs):
    try:
      return self.func(*args, **kwargs)
    except Exception, e:
      if hasattr(self.func, 'im_self') and \
            isinstance(self.func.im_self, ViewportPlugin) and \
            self.func.im_self.parent:
        error_message = PluginErrorMessage(
          traceback.format_exception_only(e.__class__, e)[0].strip(), 
          traceback.format_exc())
        error_message.add_button(gtk.STOCK_REFRESH, gtk.RESPONSE_APPLY)
        error_message.connect('response', self.func.im_self._onMessageResponse)
        self.func.im_self.message_area.pack_start(error_message)
        error_message.show_all()
      else:
        raise e

  def __eq__(self, other):
    '''
    Compare the held function and instance with that held by another wrapper.
    
    @param other: Another wrapper object
    @type other: L{PluginMethodWrapper}
    @return: Whether this func/inst pair is equal to the one in the other wrapper
      object or not
    @rtype: boolean
    '''
    try:
      return self.func == other.func
    except Exception:
      return False

class PluginMessage(gtk.Frame):
  __gsignals__ = {'response' : 
                  (gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, 
                   (gobject.TYPE_INT,))}
  def __init__(self):
    gtk.Frame.__init__(self)
    self.vbox = gtk.VBox()
    self.vbox.set_spacing(3)
    self.action_area = gtk.VBox()
    self.action_area.set_homogeneous(True)
    tooltip = gtk.Tooltips()
    tooltip.force_window()
    tooltip.tip_window.ensure_style()
    self.message_style = tooltip.tip_window.rc_get_style()
    event_box = gtk.EventBox()
    event_box.set_style(self.message_style)
    self.add(event_box)
    hbox = gtk.HBox()
    event_box.add(hbox)
    hbox.pack_start(self.vbox, padding=3)
    hbox.pack_start(self.action_area, False, False, 3)

  def add_button(self, button_text, response_id):
    button = gtk.Button()
    button.set_use_stock(True)
    button.set_label(button_text)
    button.connect('clicked', self._onActionActivated, response_id)
    self.action_area.pack_start(button, False, False)
    return button

  def _onActionActivated(self, button, response_id):
    self.emit('response', response_id)

class PluginErrorMessage(PluginMessage):
  def __init__(self, error_message, details):
    PluginMessage.__init__(self)
    hbox = gtk.HBox()
    hbox.set_spacing(6)
    self.vbox.pack_start(hbox, False, False)
    image = gtk.Image()
    image.set_from_stock(gtk.STOCK_DIALOG_WARNING,
                         gtk.ICON_SIZE_SMALL_TOOLBAR)
    hbox.pack_start(image, False, False)
    label = gtk.Label()
    label.set_ellipsize(pango.ELLIPSIZE_END)
    label.set_selectable(True)
    label.set_markup('<b>%s</b>' % error_message)
    hbox.pack_start(label)
    label = gtk.Label(details)
    label.set_ellipsize(pango.ELLIPSIZE_END)
    label.set_selectable(True)
    self.vbox.add(label)
    self.add_button(gtk.STOCK_CLEAR, gtk.RESPONSE_CLOSE)

  
