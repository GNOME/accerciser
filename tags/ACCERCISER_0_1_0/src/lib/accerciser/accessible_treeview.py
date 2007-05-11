'''
Defines behavior of the accessible tree view widget.

@author: Peter Parente
@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2006, 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import gtk
import gobject
import pyLinAcc
import atk, os
from icons import getIcon
from node import Node
from tools import Tools
from i18n import _

COL_ICON = 0
COL_NAME = 1
COL_ROLE = 2
COL_CHILDCOUNT = 3
COL_FILLED = 4
COL_ACC = 5

class AccessibleModel(gtk.TreeStore, Tools):
  def __init__(self, desktop_acc):
    self.acc_cache = [desktop_acc]
    gtk.TreeStore.__init__(self, gtk.gdk.Pixbuf, str, str, str, bool, object)
    self.connect('row-changed', self._onRowChanged)
    self.desktop = desktop_acc

  def _onRowChanged(self, model, path, iter):
    self._prepopLevel(model[iter][COL_ACC], iter)

  def insert(self, iter, index, row):
    acc = row[COL_ACC]
    if acc:
      self.acc_cache.append(acc)
    new_iter = gtk.TreeStore.insert(self, iter, index, row)
    self._prepopLevel(acc, new_iter)

  def append(self, iter, row):
    self.insert(iter, -1, row)

  def remove(self, iter):
    if self[iter][COL_ACC]:
      self.acc_cache.remove(self[iter][COL_ACC])
    return gtk.TreeStore.remove(self, iter)

  def isInModel(self, acc):
    return acc in self.acc_cache

  def getChildrenAccs(self, iter):
    if iter:
      return [row[COL_ACC] for row in self[iter].iterchildren()]
    else:
      return [row[COL_ACC] for row in self]

  def _prepopLevel(self, parent, iter):
    if (parent and parent.childCount > 0 and 
        not self.isMyApp(parent) and self.iter_n_children(iter) == 0):
      row = self._buildRow(None, False)
      self.append(iter, row)

  def popLevel(self, parent, iter):
    iters = []
    if parent is None:
      return iters
    for child in parent:
      if child is None:
        row = self._buildRow(None, False, '<dead>')
        citer = self.append(iter, row)
      else:
        row = self._buildRow(child, False)
        citer = self.append(iter, row)
      iters.append(citer)
    return iters

  def getAccPath(self, acc):
    path = ()
    child = acc
    while child.parent:
      try:
        path = (child.getIndexInParent(),) + path
      except Exception, e:
        return None
      child = child.parent
    try:
      path = (list(self.desktop).index(child),) + path
    except Exception, e:
      return None
    return path

  def _buildRow(self, accessible, filled, name=None):
    '''
    Wrapper for building a row in the tree. Use this method instead of trying
    to construct the row by hand as it will be synced with the design of the
    model fields.

    @param accessible: Accessible object
    @type accessible: pyLinAcc.Accessible
    @param filled: Should the row be considered populated?
    @type filled: boolean
    @param name: Optional name to use as an override for the name gotten from
      the accessible
    @type name: string
    '''
    if accessible is not None:
      icon = getIcon(accessible)
      name = name or accessible.name
      role = accessible.getLocalizedRoleName()
      count = str(accessible.childCount)
    else:
      icon = None
      name = name or None
      role = None
      count = None
    return [icon, name, role, count, filled, accessible]

class AccessibleTreeView(gtk.TreeView, Tools):
  def __init__(self):
    gtk.TreeView.__init__(self)

    self.desktop = pyLinAcc.Registry.getDesktop(0)
    self.node = Node()
    self.node.update(self.desktop)
    self.changed_handler = self.node.connect('accessible_changed',
                                             self._onAccChanged)
    self.connect('row-activated', self._onRowActivated)

    self.model = AccessibleModel(self.desktop)
    self.set_model(self.model)
    crt = gtk.CellRendererText()
    crp = gtk.CellRendererPixbuf()
    tvc = gtk.TreeViewColumn(_('Name'))
    tvc.pack_start(crp, False)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crp, pixbuf=COL_ICON)
    tvc.set_attributes(crt, text=COL_NAME)
    tvc.set_resizable(True)
    tvc.set_cell_data_func(crt, self._accCellDataFunc)
    tvc.set_cell_data_func(crp, self._accCellDataFunc)
    self.append_column(tvc)
    crt= gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Role'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=COL_ROLE)
    tvc.set_resizable(True)
    tvc.set_cell_data_func(crt, self._accCellDataFunc)
    self.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Children'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=COL_CHILDCOUNT)
    tvc.set_resizable(True)
    tvc.set_cell_data_func(crt, self._accCellDataFunc)
    self.append_column(tvc)

    self.refreshTopLevel()

    selection = self.get_selection()
    selection.unselect_all()
    selection.connect('changed', self._onSelectionChanged)
    selection.set_select_function(self._selectFunc, full=True)
    self.connect('row-expanded', self._onExpanded)
    self.event_manager = pyLinAcc.Event.Manager()
    self.event_manager.addClient(self._accEventChildChanged, 
                                 'object:children-changed')

  def destroy(self):
    self.event_manager.close()
    gtk.TreeView.destroy(self)

  def refreshTopLevel(self):
    '''
    Refreshes the entire tree at the desktop level.
    '''
    self.model.clear()
    iters = self.model.popLevel(self.desktop, None)
    # iter over all apps in the desktop too
    
  def refreshCurrentLevel(self):
    '''
    Refreshes the current level. Selects and expands the parent of the level.
    '''
    selection = self.get_selection()
    model, iter = selection.get_selected()
    is_expanded = self.row_expanded(self.model.get_path(iter))
    self._refreshChildren(iter)
    if is_expanded:
      self.expand_row(self.model.get_path(iter), False)
      self._onExpanded(self, iter, self.model.get_path(iter))

  def _onExpanded(self, tv, iter, path):
    '''
    Populates a level when it is expanded. Removes the previously added dummy
    node. Pre-populates the next level so expand spinners are correctly shown
    for all children having children.
    '''
    # don't repopulate if it has been filled before
    if self.model[iter][COL_FILLED]:
      return
    self.model[iter][COL_FILLED] = True
    acc = self.model[iter][COL_ACC]
    # populate this level
    self.model.popLevel(acc, iter)
    # clear the dummy node from this level
    self.model.remove(self.model.iter_children(iter))

  def _accEventChildChanged(self, event):
    if self.isMyApp(event.source):
      # Bad karma
      return
    if self.model.isInModel(event.source):
      path = self.model.getAccPath(event.source)
      if path:
        iter = self.model.get_iter(path)
      else:
        iter = None
      if (event.source == self.desktop) or \
            (path and self.model[path][COL_FILLED]):
        if event.type.minor == 'add':
          self._addChild(iter, event.source)
        elif event.type.minor == 'remove':
          self._removeChild(iter, event.source)
      if iter and self.model.iter_is_valid(iter):
        self.model[iter][COL_CHILDCOUNT] = str(event.source.childCount)

  def _addChild(self, iter, parent):
    old_children = set(self.model.getChildrenAccs(iter))
    new_children = set(list(parent))
    added = new_children.difference(old_children)
    try:
      new_child = added.pop()
    except KeyError:
      return
    if new_child is None:
      row = self.model._buildRow(new_child, False, name='<dead>')
      self.model.append(iter, row)
      return
    else:
      row = self.model._buildRow(new_child, False)
      self.model.insert(iter, new_child.getIndexInParent(), row)
    # We do this because an application won't have an icon loaded in 
    # the window manager when it is first registered to at-spi
    if new_child == new_child.getApplication():
      gobject.timeout_add(1000, self._refreshIcon, new_child)
    
  def _refreshIcon(self, app):
    path = self.model.getAccPath(app)
    try:
      self.model[path][COL_ICON] = getIcon(app)
    except:
      pass
    return False

  def _removeChild(self, parent_iter, parent):
    if parent_iter:
      iter = self.model.iter_children(parent_iter)
    else:
      iter = self.model.get_iter_root()
    while iter:
      if self.model[iter][COL_ACC] not in parent:
        if not self.model.remove(iter):
          break
      else:
        iter = self.model.iter_next(iter)


  def _refreshChildren(self, iter):
    if not iter:
      self.refreshTopLevel()
      return
    child_iter = self.model.iter_children(iter)
    while child_iter:
      if not self.model.remove(child_iter):
        break
    acc = self.model[iter][COL_ACC]
    self.model[iter][COL_CHILDCOUNT] = acc.childCount
    self.model[iter][COL_FILLED] = False

  def refreshSelected(self):
    selection = self.get_selection()
    model, iter = selection.get_selected()
    self._refreshChildren(iter)

  def _onSelectionChanged(self, selection):
    model, iter = selection.get_selected()
    try:
      new_acc = model[iter][COL_ACC]
    except TypeError:
      new_acc = self.desktop
    if new_acc == self.node.acc:
      return
    self.node.handler_block(self.changed_handler)
    self.node.update(new_acc)
    self.node.handler_unblock(self.changed_handler)

  def _onAccChanged(self, node, acc):
    if self.isMyApp(acc):
      # Bad karma
      return
    path = self.model.getAccPath(acc)
    if not path:
      return
    if len(path) > 1:
      self.expand_to_path(path[:-1])
    self.scroll_to_cell(path)
    selection = self.get_selection()
    try:
      selection.select_iter(self.model.get_iter(path))
    except ValueError:
      pass

  def _accCellDataFunc(self, tvc, cellrenderer, model, iter):
    if model.iter_is_valid(iter):
      acc = model.get_value(iter, COL_ACC)
    else:
      acc = None
    if self.isMyApp(acc):
      cellrenderer.set_property('sensitive', False)
    else:
      cellrenderer.set_property('sensitive', True)

  def _selectFunc(self, selection, model, path, is_selected):
    acc = model[path][COL_ACC]
    return not self.isMyApp(acc)

  def _onRowActivated(self, treeview, path, view_column):
    self.node.blinkRect()
