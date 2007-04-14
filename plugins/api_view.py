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
import gtk
import accerciser.plugin
from accerciser.i18n import _
from pyLinAcc import *

class DemoViewport(accerciser.plugin.ViewportPlugin):
  plugin_name = 'API Browser'
  plugin_description = 'Browse the various methods of the current accessible'
  def init(self):
    self._buildUI()
    self._initModels()
    self.iface_combo.connect('changed', self._refreshAttribs)
    self.private_toggle.connect('toggled', self._refreshAttribs)
    self.curr_iface = None
    self.constructors = {}
    for iface in dir(Interfaces):
      if iface.startswith('I'):
        self.constructors[iface[1:].lower()] = getattr(Interfaces, iface)

  def _buildUI(self):
    vbox = gtk.VBox()
    self.plugin_area.add(vbox)
    top_hbox = gtk.HBox()
    bottom_hbox = gtk.HBox()
    vbox.pack_start(top_hbox)
    vbox.pack_start(bottom_hbox, False)
    self.method_tree = gtk.TreeView()
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.add(self.method_tree)
    top_hbox.pack_start(scrolled_window)
    self.property_tree = gtk.TreeView()
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.add(self.property_tree)
    top_hbox.pack_start(scrolled_window)
    self.iface_combo = gtk.combo_box_new_text() 
    bottom_hbox.pack_start(self.iface_combo, False)
    self.private_toggle = gtk.CheckButton(_('Hide private attributes'))
    self.private_toggle.set_active(True)
    bottom_hbox.pack_end(self.private_toggle, False)
    self.show_all()
    
  def _initModels(self):
    # method view
    model = gtk.ListStore(str, str)
    self.method_tree.set_model(model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Method'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=0)
    self.method_tree.append_column(tvc)
    
    # property view
    model = gtk.ListStore(str, str)
    self.property_tree.set_model(model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Property'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=0)
    self.property_tree.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Value'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=1)
    self.property_tree.append_column(tvc)

  def onAccChanged(self, acc):
    self.acc = acc
    ints = self._getInterfaces(acc)
    model = self.iface_combo.get_model()
    model.clear()
    for iface in ints:
      self.iface_combo.append_text(iface)
    self.iface_combo.set_active(0)

  def _getInterfaces(self, acc):
    ints = []
    for func in (f for f in Interfaces.__dict__.values() 
                 if callable(f) and f.func_name.startswith('I')):
      try:
        i = func(acc)
      except Exception:
        pass
      else:
        ints.append(func.func_name[1:].lower())
    ints.sort()
    return ints
  
  def _refreshAttribs(self, widget):
    iface = self.iface_combo.get_active_text()
    try:
      self.curr_iface = self.constructors[iface](self.acc)
    except KeyError:
      pass
    else:
      self._popAttribViews()

  def _popAttribViews(self):
    prop_model = self.property_tree.get_model()
    method_model = self.method_tree.get_model()
    prop_model.clear()
    method_model.clear()
    for attr in dir(self.curr_iface):
      if self.private_toggle.get_active() and attr[0] == '_':
        continue
      obj = getattr(self.curr_iface, attr)
      if callable(obj):
        method_model.append([attr, obj.__doc__])
      else:
        prop_model.append([attr, str(obj)])
