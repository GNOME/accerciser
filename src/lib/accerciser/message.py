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

import gtk, gobject, pango
from i18n import _

class MessageManager(gobject.GObject):
  __gsignals__ = {'plugin-reload-request' :
                    (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, 
                     (gobject.TYPE_PYOBJECT,
                      gobject.TYPE_PYOBJECT)),
                  'module-reload-request' :
                    (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, 
                     (gobject.TYPE_PYOBJECT,
                      gobject.TYPE_STRING,
                      gobject.TYPE_STRING))}
  def __init__(self):
    gobject.GObject.__init__(self)
    self.message_tab = None

  def getMessageTab(self):
    if not self.message_tab:
      self.message_tab = self.MessageTab()
    return self.message_tab

  def newError(self, error_message, details):
    plugin_error_message = PluginErrorMessage(error_message, details)
    plugin_error_message.add_button(gtk.STOCK_REFRESH, gtk.RESPONSE_APPLY)
    plugin_error_message.connect('response', self._onResponse)
    return plugin_error_message

  def newPluginError(self, plugin_instance, plugin_class, 
                     error_message, details):
    message = self.newError(error_message, details)
    message.connect('response', self._onPluginResponseRefresh, plugin_class)
    if getattr(plugin_instance, 'parent', None):
      plugin_instance.message_area.pack_start(message)
      message.show_all()
    else:
      self.message_tab.addMessage(plugin_error_message)
    return message

  def _onPluginResponseRefresh(self, message, response_id, plugin_class):
    if response_id == gtk.RESPONSE_APPLY:
      self.emit('plugin-reload-request', message, plugin_class)

  def newModuleError(self, module, path, error_message, details):
    message = self.newError(error_message, details)
    message.connect('response', self._onModuleResponseRefresh, module, path)
    self.message_tab.addMessage(message)
    return message

  def _onModuleResponseRefresh(self, message, response_id, module, path):
    if response_id == gtk.RESPONSE_APPLY:
      self.emit('module-reload-request', message, module, path)

  def _onResponse(self, plugin_message, response_id):
    if response_id == gtk.RESPONSE_CLOSE:
      plugin_message.destroy()

  class MessageTab(gtk.ScrolledWindow):
    def __init__(self):
      gtk.ScrolledWindow.__init__(self)
      self.set_name(_('Plugin Errors'))
      self._vbox = gtk.VBox()
      self._vbox.connect('remove', self._onMessageRemove)
      self.add_with_viewport(self._vbox)
      self.set_no_show_all(True)

    def addMessage(self, message):
      self._vbox.pack_start(message, False)
      self.show()
      self._vbox.show_all()
      
    def removeMessage(self, message):
      message.destroy()

    def _onMessageRemove(self, vbox, message):
      if len(vbox.get_children()) == 0:
        self.hide()
        
class PluginMessage(gtk.Frame):
  '''
  Pretty plugin message area that appears either above the plugin if the plugin
  is realized or in a seperate view.

  @ivar vbox: Main contents container.
  @type vbox: gtk.VBox
  @ivar action_area: Area used mainly for response buttons.
  @type action_area: gtk.VBox
  @ivar message_style: Tooltip style used for mesages.
  @type message_style: gtk.Style
  '''
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
    '''
    Add a button to the action area that emits a response when clicked.
    
    @param button_text: The button text, or a stock ID.
    @type button_text: string
    @param response_id: The response emitted when the button is pressed.
    @type response_id: integer
    
    @return: Return the created button.
    @rtype: gtk.Button
    '''
    button = gtk.Button()
    button.set_use_stock(True)
    button.set_label(button_text)
    button.connect('clicked', self._onActionActivated, response_id)
    self.action_area.pack_start(button, False, False)
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
  def __init__(self, error_message, details):
    '''
    Plugin error message.
    
    @param error_message: The error message.
    @type error_message: string
    @param details: Further details about the error.
    @type details: string
    '''
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

  
