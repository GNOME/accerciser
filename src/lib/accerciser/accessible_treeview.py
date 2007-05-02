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
import pyatspi
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
  '''
  Stores the desktop accessible tree. Only populates sections of the tree
  that are being viewed. This cuts short on a lot of potential overhead.

  @ivar desktop: The desktop accessible. It holds references to all the 
  application L{pyLinAcc.Accessible}s
  @type desktop: L{pyLinAcc.Accessible}
  @ivar acc_cache: A list of L{pyLinAcc.Accessible}s that are currently
  resident in the model. This helps with faster searching.
  @type acc_cache: list
  '''
  def __init__(self, desktop_acc):
    '''
    Initializes the L{AccessibleModel} and all of the needed instant variables.
    Connects required signals.
    '''
    self.acc_cache = [desktop_acc]
    gtk.TreeStore.__init__(self, gtk.gdk.Pixbuf, str, str, str, bool, object)
    self.connect('row-changed', self._onRowChanged)
    self.desktop = desktop_acc

  def _onRowChanged(self, model, path, iter):
    '''
    A callback on "row-changed" that pre-populates a given row when it changes.

    @param model: This model.
    @type model: L{AccessibleModel}
    @param path: The path to the row that changed.
    @type path: tuple
    @param iter: the iter of the row that changed.
    @type iter: L{gtk.TreeIter}
    '''
    self._prepopLevel(model[iter][COL_ACC], iter)

  def insert(self, iter, index, row):
    '''
    A method that overrides the L{gtk.TreeStore} insert method.
    Pre-populate and add the new accessible to acc_cache.

    @param iter: The parent iter of the newly inserted row.
    @type iter: L{gtk.TreeIter}
    @param index: The place in which to insert the new row.
    @type index: integer
    @param row: A list of columns o insert into the row,
    @type row: list

    @return: The newly created iter of the inserted row.
    @rtype: L{gtk.TreeIter}
    '''
    acc = row[COL_ACC]
    if acc:
      self.acc_cache.append(acc)
    new_iter = gtk.TreeStore.insert(self, iter, index, row)
    self._prepopLevel(acc, new_iter)

  def append(self, iter, row):
    '''
    A method that overrides the L{gtk.TreeStore} append method.
    Pre-populate and add the new accessible to acc_cache.

    @param iter: The parent iter of the newly inseted row.
    @type iter: L{gtk.TreeIter}
    @param row: A list of columns o insert into the row,
    @type row: list

    @return: The newly created iter of the inserted row.
    @rtype: L{gtk.TreeIter}
    '''
    self.insert(iter, -1, row)
    
  def remove(self, iter):
    '''
    A method that overrides the L{gtk.TreeStore} remove method.
    Remove the row's accessible from acc_cache.

    @param iter: The parent iter of the newly inserted row.
    @type iter: L{gtk.TreeIter}

    @return: True if L{iter} is still valid.
    @rtype: boolean
    '''
    if self[iter][COL_ACC]:
      self.acc_cache.remove(self[iter][COL_ACC])
    return gtk.TreeStore.remove(self, iter)

  def isInModel(self, acc):
    '''
    Checks if the given L{pyLinAcc.Accessible} is resident in the model.

    @param acc: The L{pyLinAcc.Accessible} to check.
    @type acc: L{pyLinAcc.Accessible}

    @return: True if it is in the model.
    @rtype: boolean
    '''
    return acc in self.acc_cache

  def getChildrenAccs(self, iter):
    '''
    Get list of accessible children of a given row.

    I{Note:} This method returns the accessible's children as they currently exist in 
    the model. The list of accessibles is not necessarily identical to the actual 
    children of the accessible at the given row.

    @param iter: Th iter of the row that we want it's children
    @type iter: L{gtk.TreeIter}

    @return: List of children
    @rtype: list
    '''
    if iter:
      return [row[COL_ACC] for row in self[iter].iterchildren()]
    else:
      return [row[COL_ACC] for row in self]

  def _prepopLevel(self, parent, iter):
    '''
    Pre-populate a row. If a L{pyLinAcc.Accessible} of the given row has children,
    we need to add to it one dummy child row so that the expander will show and
    enable the user to expand it. We populate the children rows at expansion time.

    @param parent: The given row's accessible.
    @type parent: L{pyLinAcc.Accessible}
    @param iter: Th iter of the row that needs to be pre-populated
    @type iter: L{gtk.TreeIter}
    '''
    if (parent and parent.childCount > 0 and 
        not self.isMyApp(parent) and self.iter_n_children(iter) == 0):
      row = self._buildRow(None, False)
      self.append(iter, row)

  def popLevel(self, parent, iter):
    '''
    Populate a row with children rows, according to the row's accessible's children.

    @param parent: The given row's accessible.
    @type parent: L{pyLinAcc.Accessible}
    @param iter: Th iter of the row that needs to be populated
    @type iter: L{gtk.TreeIter}
    
    @return: A list of L{gtk.TreeIter}s that have been inserted.
    @rtype: list
    '''
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
    '''
    Get the tree path that a given accessible should have.
    
    I{Note:} The accessible does not necessarily need to be resident in the model.
    
    @param acc: The accessible we want a path of.
    @type acc: L{pyLinAcc.Accessible}
    
    @return: The path to the accessible.
    @rtype: tuple
    '''
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
  '''
  The treeview for the desktop's accessibles. The treeview's model (L{AccessibleModel}
  is only populated when the treeview is traversed and nodes are expanded. This class
  listens for 'row-expanded' events in order to have a tree node populated. Nodes that
  are selected are updated into the L{Node} instance variable. This treeview also 
  updates automatically in response to at-spi children change events.

  @ivar desktop: The desktop accessible. It holds references to all the 
  application L{pyLinAcc.Accessible}s
  @type desktop: L{pyLinAcc.Accessible}
  @ivar node: An object with a reference to the currently selected accessible.
  @type node: L{Node}
  @ivar model: The data model of this treeview.
  @type model: L{AccessibleModel}
  @ivar event_manager: The event manager we use for handling at-spi events.
  @type event_manager: L{pyLinAcc.Event.Manager}
  '''
  def __init__(self):
    '''
    Initialize the treeview. Build the proper columns.
    Connect all of the proper signal handlers and at-spi event handlers.
    '''
    gtk.TreeView.__init__(self)

    self.desktop = pyatspi.Registry.getDesktop(0)
    self.node = Node()
    self.node.update(self.desktop)
    self._changed_handler = self.node.connect('accessible_changed',
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
    pyatspi.Registry.registerEventListener(self._accEventChildChanged, 
                                           'object:children-changed')

  def destroy(self):
    '''
    Overrides superclass's destroy method.
    Used for explicitly closing the L{pyLinAcc.Event.Manager} or bad things happen.
    '''
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

  def _onExpanded(self, treeview, iter, path):
    '''
    Populates a level when it is expanded. Removes the previously added dummy
    node.

    @param treeview: The L{AccessibleTreeView} that emitted the signal.
    @type treeview: L{AccessibleTreeView}
    @param iter: The iter that has been expanded.
    @type iter: L{gtk.TreeIter}
    @param path: The path to the row that has been expanded.
    @type path: tuple
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
    '''
    Event handler for "object:children-changed". Updates the treeview accordingly.
    
    @param event: The event which triggered this handler.
    @type event: L{pyLinAcc.Event}
    '''
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
    '''
    Add the new child to the given accessible.

    @param iter: Th iter of the row that needs a child added. 
    @type iter: L{gtk.TreeIter}
    @param parent: The given row's accessible.
    @type parent: L{pyLinAcc.Accessible}
    '''
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
    '''
    Refresh the icon of a given application's accessible. This is done because it
    takes wnck a while to load an application's icon at application startup.

    @param app: The given application's accessible.
    @type app: L{pyLinAcc.Accessible}
    '''
    path = self.model.getAccPath(app)
    try:
      self.model[path][COL_ICON] = getIcon(app)
    except:
      pass
    return False

  def _removeChild(self, parent_iter, parent):
    '''
    Remove a child from the given accessible node.

    @param parent_iter: Th iter of the row that needs a child removed. 
    @type parent_iter: L{gtk.TreeIter}
    @param parent: The given row's accessible.
    @type parent: L{pyLinAcc.Accessible}
    '''
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
    '''
    Remove all of a given node's children from the model.

    @param iter: The parent node.
    @type iter: L{gtk.TreeIter}
    '''
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
    '''
    Manually refresh the selected node.
    '''
    selection = self.get_selection()
    model, iter = selection.get_selected()
    self._refreshChildren(iter)

  def _onSelectionChanged(self, selection):
    '''
    Update the accessible according to the selected row.

    @param selection: The selection object that emitted the the 'selection-changed'
    signal.
    @type selection: L{gtk.TreeSelection}
    '''
    model, iter = selection.get_selected()
    try:
      new_acc = model[iter][COL_ACC]
    except TypeError:
      new_acc = self.desktop
    if new_acc == self.node.acc:
      return
    self.node.handler_block(self._changed_handler)
    self.node.update(new_acc)
    self.node.handler_unblock(self._changed_handler)

  def _onAccChanged(self, node, acc):
    '''
    Change the treeview's selection to the updated accessible in the L{Node}.

    @param node: The L{node} that emitted the signal.
    @type node: L{Node}
    @param acc: The new accessible in the node.
    @type acc: L{pyLinAcc.Accessible}
    '''
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
    '''
    A cellrenderer data function. renderer's this application's node as insensitive.

    @param tvc: A treeview column.
    @type tvc: L{gtk.TreeViewColumn}
    @param cellrenderer: The cellrenderer that needs to be tweaked.
    @type cellrenderer: L{gtk.CellRenderer}
    @param model: The treeview's data model.
    @type model: L{AccessibleModel}
    @param iter: The iter at the given row.
    @type iter: L{gtk.TreeIter}
    '''
    if model.iter_is_valid(iter):
      acc = model.get_value(iter, COL_ACC)
    else:
      acc = None
    if self.isMyApp(acc):
      cellrenderer.set_property('sensitive', False)
    else:
      cellrenderer.set_property('sensitive', True)

  def _selectFunc(self, selection, model, path, is_selected):
    '''
    A selection function. Does not allow his application's node to be selected.

    @param selection: The given selection object.
    @type selection: L{gtk.TreeSelection}
    @param model:The treeview's data model.
    @type model: L{AccessibleModel}
    @param path: The path to the selected row.
    @type path: tuple
    @param is_selected: True if the path is selected.
    @type is_selected: boolean

    @return: True if the row's accessible is not this app.
    @rtype: boolean
    '''
    acc = model[path][COL_ACC]
    return not self.isMyApp(acc)

  def _onRowActivated(self, treeview, path, view_column):
    '''
    When the row is activated (double clicked, or enter), blink the selected 
    accessible, if possible.

    @param treeview: The L{AccessibleTreeView} that emitted the signal.
    @type treeview: L{AccessibleTreeView}
    @param path: The path to the selected row.
    @type path: tuple
    @param view_column: The column in the activated row.
    @type view_column: L{gtk.TreeViewColumn}
    '''
    self.node.blinkRect()
