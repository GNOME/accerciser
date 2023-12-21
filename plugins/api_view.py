'''
AT-SPI API browser plugin.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''
from gi.repository import Gtk as gtk
from accerciser.plugin import ViewportPlugin
from accerciser.i18n import _, N_
import pyatspi

class APIBrowser(ViewportPlugin):
  '''
  Plugin class for API Browser.

  @ivar iface_combo: Combobox that shows available interfaces.
  @type iface_combo: gtk.ComboBox
  @ivar method_tree: Tree view with available methods from chosen interface.
  @type method_tree: gtk.TreeView
  @ivar property_tree: Tree view with available properties from chosen
  interface.
  @type property_tree: gtk.TreeView
  @ivar private_toggle: Toggles visibility of private attributes.
  @type private_toggle: gtk.CheckButton
  '''
  plugin_name = N_('API Browser')
  plugin_name_localized = _(plugin_name)
  plugin_description = \
      N_('Browse the various methods of the current accessible')
  def init(self):
    '''
    Initialize the API browser plugin.
    '''
    self._buildUI()
    self._initTreeViews()
    self.iface_combo.connect('changed', self._refreshAttribs)
    self.private_toggle.connect('toggled', self._refreshAttribs)
    self.curr_iface = None

  def _buildUI(self):
    '''
    Manually build the plugin's UI.
    '''
    vbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)
    self.plugin_area.add(vbox)
    top_hbox = gtk.Box()
    bottom_hbox = gtk.Box()
    vbox.pack_start(top_hbox, False, True, 0)
    vbox.pack_start(bottom_hbox, True, True, 0)
    self.method_tree = gtk.TreeView()
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.add(self.method_tree)
    bottom_hbox.pack_start(scrolled_window, True, True, 0)
    self.property_tree = gtk.TreeView()
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.add(self.property_tree)
    bottom_hbox.pack_start(scrolled_window, True, True, 0)
    self.iface_combo = gtk.ComboBoxText.new()
    top_hbox.pack_start(self.iface_combo, False, True, 0)
    self.private_toggle = gtk.CheckButton.new_with_label(_('Hide private attributes'))
    self.private_toggle.set_active(True)
    top_hbox.pack_end(self.private_toggle, False, True, 0)
    self.show_all()

  def _initTreeViews(self):
    '''
    Initialize the properties and methods tree views and models.
    '''
    # method view
    model = gtk.ListStore(str, str)
    self.method_tree.set_model(model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Method'))
    tvc.pack_start(crt, True)
    tvc.add_attribute(crt, 'text', 0)
    self.method_tree.append_column(tvc)

    # property view
    model = gtk.ListStore(str, str)
    self.property_tree.set_model(model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Property'))
    tvc.pack_start(crt, True)
    tvc.add_attribute(crt, 'text', 0)
    self.property_tree.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Value'))
    tvc.pack_start(crt, True)
    tvc.add_attribute(crt, 'text', 1)
    self.property_tree.append_column(tvc)

  def onAccChanged(self, acc):
    '''
    Update the UI when the selected accessible changes.

    @param acc: The applications-wide selected accessible.
    @type acc: Accessibility.Accessible
    '''
    self.acc = acc
    ints = pyatspi.listInterfaces(acc)
    model = self.iface_combo.get_model()
    model.clear()
    for iface in ints:
      self.iface_combo.append_text(iface)
    self.iface_combo.set_active(0)

  def _refreshAttribs(self, widget):
    '''
    Refresh the attributes in the tree views. Could be used as a callback.

    @param widget: The widget that may have triggered this callback.
    @type widget: gtk.Widget
    '''
    iface = self.iface_combo.get_active_text()

    try:
      query_func = getattr(self.acc, 'query%s' % iface)
    except AttributeError:
      pass
    else:
      self.curr_iface = query_func()
      self._popAttribViews()

  def _popAttribViews(self):
    '''
    Populate the attribute views with information from currently selected
    accessible and interface.
    '''
    prop_model = self.property_tree.get_model()
    method_model = self.method_tree.get_model()
    prop_model.clear()
    method_model.clear()
    for attr in dir(self.curr_iface):
      if self.private_toggle.get_active() and attr[0] == '_':
        continue
      try:
        obj = getattr(self.curr_iface, attr)
      except AttributeError:
        # Slots seem to raise AttributeError if they were not assigned.
        continue
      if callable(obj):
        method_model.append([attr, obj.__doc__])
      else:
        prop_model.append([attr, str(obj)])
