'''
Defines all plugin-related messaging elements.

@author: Eitan Isaacson
@organization: Mozilla Foundation
@copyright: Copyright (c) 2006, 2007 Mozilla Foundation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import gi

from gi.repository import Gtk as gtk
from gi.repository import GObject
from gi.repository import Pango

from accerciser.i18n import _

class MessageManager(GObject.GObject):
  '''
  Centralizes all plugin message handling. If the plugin is a visible widget,
  it displays the message within the plugin. If not it displays the message in
  a dedicated message tab.

  This manager also could emit module and plugin reload requests from user
  responses to messages.
  '''
  __gsignals__ = {'plugin-reload-request' :
                    (GObject.SignalFlags.RUN_FIRST,
                     None,
                     (GObject.TYPE_PYOBJECT,
                      GObject.TYPE_PYOBJECT)),
                  'module-reload-request' :
                    (GObject.SignalFlags.RUN_FIRST,
                     None,
                     (GObject.TYPE_PYOBJECT,
                      GObject.TYPE_STRING,
                      GObject.TYPE_STRING))}
  def __init__(self):
    '''
    Initialize the manager.
    '''
    GObject.GObject.__init__(self)
    self.message_tab = None

  def getMessageTab(self):
    '''
    Get the manager's dedicated message tab. Initialize a message tab if
    one does not already exist.

    @return: The message tab.
    @rtype: L{MessageManager.MessageTab}
    '''
    if not self.message_tab:
      self.message_tab = self.MessageTab()
    return self.message_tab

  def newPluginError(self, plugin_instance, plugin_class,
                     error_message, details):
    '''
    Create a new plugin error message, and display it eithe in the plugin
    itself or in the error tab.

    @param plugin_instance: Plugin instance that had the error.
    @type plugin_instance: L{Plugin}
    @param plugin_class: Plugin class.
    @type plugin_class: type
    @param error_message: Principal error message.
    @type error_message: string
    @param details: Detailed error message.
    @type details: string

    @return: The newly created error message.
    @rtype: L{PluginErrorMessage}
    '''
    message = PluginErrorMessage(error_message, details)
    message.connect('response', self._onPluginResponseRefresh, plugin_class)
    if getattr(plugin_instance, 'parent', None):
      plugin_instance.message_area.pack_start(message, True, True, 0)
      message.show_all()
    else:
      self.message_tab.addMessage(message)
    return message

  def _onPluginResponseRefresh(self, message, response_id, plugin_class):
    '''
    Callback for gtk.RESPONSE_APPLY of a plugin error message, emits a plugin
    reload request signal.

    @param message: Error message that emitted response signal.
    @type message: L{PluginErrorMessage}
    @param response_id: The response ID.
    @type response_id: integer
    @param plugin_class: The plugin class of the failed plugin.
    @type plugin_class: type
    '''
    if response_id == gtk.ResponseType.APPLY:
      self.emit('plugin-reload-request', message, plugin_class)

  def newModuleError(self, module, path, error_message, details):
    '''
    Create a new module error dialog. Usually because of a syntax error
    in a module. Put error message in message tab.

    @param module: Failed module name.
    @type module: string
    @param path: Failed module's path.
    @type path: string
    @param error_message: Principal error message.
    @type error_message: string
    @param details: Detailed error message.
    @type details: string

    @return: The newly created error message.
    @rtype: L{PluginErrorMessage}
    '''
    message = PluginErrorMessage(error_message, details)
    message.connect('response', self._onModuleResponseRefresh, module, path)
    self.message_tab.addMessage(message)
    return message

  def _onModuleResponseRefresh(self, message, response_id, module, path):
    '''
    Callback for gtk.RESPONSE_APPLY of a module error message, emits a module
    reload request signal.


    @param message: Error message that emitted response signal.
    @type message: L{PluginErrorMessage}
    @param response_id: The response ID.
    @type response_id: integer
    @param module: Failed module name.
    @type module: string
    @param path: Failed module's path.
    @type path: string
    '''
    if response_id == gtk.ResponseType.APPLY:
      self.emit('module-reload-request', message, module, path)

  class MessageTab(gtk.ScrolledWindow):
    '''
    Implements a scrolled window with a box for messages that cannot be
    displayed in their plugins
    '''
    def __init__(self):
      '''
      Initialize tab.
      '''
      gtk.ScrolledWindow.__init__(self)
      self.set_name(_('Plugin Errors'))
      self._vbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)
      self._vbox.connect('remove', self._onMessageRemove)
      self.add_with_viewport(self._vbox)
      self.set_no_show_all(True)

    def addMessage(self, message):
      '''
      Add a message to the tab.

      @param message: The message to be added.
      @type message: L{PluginMessage}
      '''
      self._vbox.pack_start(message, False, True, 0)
      self.show()
      self._vbox.show_all()

    def removeMessage(self, message):
      '''
      Remove a message from the tab. Destroys it.

      @param message: The message to be removed.
      @type message: L{PluginMessage}
      '''
      message.destroy()

    def _onMessageRemove(self, box, message):
      '''
      Callback for removal of children. If there are no messages displayed,
      hide this widget.

      @param vbox: box that had a child removed.
      @type vbox: gtk.Box
      @param message: The message that was removed.
      @type message: L{PluginMessage}
      '''
      if len(box.get_children()) == 0:
        self.hide()

class PluginMessage(gtk.Frame):
  '''
  Pretty plugin message area that appears either above the plugin if the plugin
  is realized or in a seperate view.

  @ivar vbox: Main contents container.
  @type vbox: gtk.Box
  @ivar action_area: Area used mainly for response buttons.
  @type action_area: gtk.Box
  @ivar message_style: Tooltip style used for mesages.
  @type message_style: gtk.Style
  '''
  __gsignals__ = {'response' :
                  (GObject.SignalFlags.RUN_FIRST,
                   None,
                   (GObject.TYPE_INT,))}
  def __init__(self):
    '''
    Initialize the message object.
    '''
    gtk.Frame.__init__(self)
    self.vbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)
    self.vbox.set_spacing(3)
    self.action_area = gtk.Box(orientation=gtk.Orientation.VERTICAL)
    self.action_area.set_homogeneous(True)

    # Get the tooltip style, for use with the message background color.
    w = gtk.Window()
    w.set_name('gtk-tooltip')
    w.ensure_style()
    #self.message_style = w.rc_get_style()
    self.message_style = gtk.rc_get_style(w)

    event_box = gtk.EventBox()
    event_box.set_style(self.message_style)
    self.add(event_box)
    hbox = gtk.Box()
    event_box.add(hbox)
    hbox.pack_start(self.vbox, True, True, 3)
    hbox.pack_start(self.action_area, False, False, 3)

  def add_button(self, button_text, icon_name, response_id):
    '''
    Add a button to the action area that emits a response when clicked.

    @param button_text: The button text, including mnemonic.
    @type button_text: string
    @param icon_name: Icon name for icon to set for the button.
    @type icon_name: string
    @param response_id: The response emitted when the button is pressed.
    @type response_id: integer

    @return: Return the created button.
    @rtype: gtk.Button
    '''
    button = gtk.Button.new_with_mnemonic(button_text)
    button.set_image(gtk.Image.new_from_icon_name(icon_name, gtk.IconSize.BUTTON))
    button.connect('clicked', self._onActionActivated, response_id)
    self.action_area.pack_start(button, False, False, 0)
    return button

  def _onActionActivated(self, button, response_id):
    '''
    Callback for button presses that emit the correct response.

    @param button: The button that was clicked.
    @type button: gtk.Button
    @param response_id: The response ID to emit a response with.
    @type response_id: integer
    '''
    self.emit('response', response_id)

class PluginErrorMessage(PluginMessage):
  '''
  Standard error message.
  '''
  def __init__(self, error_message, details):
    '''
    Plugin error message.

    @param error_message: The error message.
    @type error_message: string
    @param details: Further details about the error.
    @type details: string
    '''
    PluginMessage.__init__(self)
    hbox = gtk.Box()
    hbox.set_spacing(6)
    self.vbox.pack_start(hbox, False, False, 0)
    image = gtk.Image.new_from_icon_name('dialog-warning',
                                         gtk.IconSize.SMALL_TOOLBAR)
    hbox.pack_start(image, False, False, 0)
    label = gtk.Label()
    label.set_ellipsize(Pango.EllipsizeMode.END)
    label.set_selectable(True)
    label.set_markup('<b>%s</b>' % error_message)
    hbox.pack_start(label, True, True, 0)
    label = gtk.Label(details)
    label.set_ellipsize(Pango.EllipsizeMode.END)
    label.set_selectable(True)
    self.vbox.add(label)
    self.add_button(_('_Clear'), 'edit-clear', gtk.ResponseType.CLOSE)
    self.add_button(_('_Refresh'), 'view-refresh', gtk.ResponseType.APPLY)
    self.connect('response', self._onResponse)

  def _onResponse(self, plugin_message, response_id):
    '''
    Destroy the message when the "clear" button is clicked.

    @param plugin_message: Message that emitted this signal.
    @type plugin_message: L{PluginErrorMessage}
    @param response_id: The response ID
    @type response_id: integer
    '''
    if response_id == gtk.ResponseType.CLOSE:
      plugin_message.destroy()
