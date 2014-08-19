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

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import GObject

import pyatspi
import os
from . import ui_manager
from time import sleep
from .icons import getIcon
from .node import Node
from .tools import Tools, getTreePathBoundingBox
from .i18n import _

COL_ICON = 0
COL_NAME = 1
COL_ROLE = 2
COL_CHILDCOUNT = 3
COL_FILLED = 4
COL_DUMMY = 5
COL_ACC = 6

ACCESSIBLE_LOADING = 5

class AccessibleModel(gtk.TreeStore, Tools):
  '''
  Stores the desktop accessible tree. Only populates sections of the tree
  that are being viewed. This cuts short on a lot of potential overhead.

  @ivar desktop: The desktop accessible. It holds references to all the 
  application L{Accessibility.Accessible}s
  @type desktop: L{Accessibility.Accessible}
  @ivar acc_cache: A list of L{Accessibility.Accessible}s that are currently
  resident in the model. This helps with faster searching.
  @type acc_cache: list
  '''
  __gsignals__ = {'row-filled' : 
                  (GObject.SignalFlags.RUN_FIRST,
                   None, 
                   (GObject.TYPE_PYOBJECT,)),
                  'start-populating' :
                    (GObject.SignalFlags.RUN_FIRST,
                     None,
                     ()),
                  'end-populating' :
                    (GObject.SignalFlags.RUN_FIRST,
                     None, 
                     ())}

  def __init__(self, desktop_acc):
    '''
    Initializes the L{AccessibleModel} and all of the needed instant variables.
    Connects required signals.
    '''
    self.acc_cache = [desktop_acc]
    gtk.TreeStore.__init__(self, GdkPixbuf.Pixbuf, str, str, str, bool, bool, object)
    self.connect('row-changed', self._onRowChanged)
    self.connect('row-filled', self._onRowFilled)
    self.desktop = desktop_acc
    self._path_to_populate = None
    self._populating_tasks = 0
    self._hide_leaves = False


  def _hideShowLeaves(self):
    '''
    Change _hide_leaves state, allowing leaves either to appear or to be hidden
    in the accessible treeview.
    '''
    self._hide_leaves = not self._hide_leaves

  def getHideLeaves(self):
    '''
    Return a boolean that indicates whether accessibles with no children
    (leaves) should be hidden.

    @return: A boolean indicating if leaves should be hidden.
    @rtype: boolean
    '''
    return self._hide_leaves

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
    Checks if the given L{Accessibility.Accessible} is resident in the model.

    @param acc: The L{Accessibility.Accessible} to check.
    @type acc: L{Accessibility.Accessible}

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
    Pre-populate a row. If a L{Accessibility.Accessible} of the given row has children,
    we need to add to it one dummy child row so that the expander will show and
    enable the user to expand it. We populate the children rows at expansion time.

    @param parent: The given row's accessible.
    @type parent: L{Accessibility.Accessible}
    @param iter: Th iter of the row that needs to be pre-populated
    @type iter: L{gtk.TreeIter}
    '''
    if (parent and self.children_number(parent) > 0 and
        not self.isMyApp(parent) and self.iter_n_children(iter) == 0):
      row = self._buildRow(None, True)
      self.append(iter, row)

  def popLevel(self, iter):
    '''
    Populate a row with children rows, according to the row's accessible's children.

    @param iter: Th iter of the row that needs to be populated
    @type iter: L{gtk.TreeIter}
    '''
    if iter:
      tree_path = self.get_path(iter)
      path = tuple(tree_path.get_indices())

      row_reference = gtk.TreeRowReference.new(self, tree_path)
      #row_reference = gtk.TreeRowReference()
    else:
      row_reference = None
    self._populating_tasks += 1
    if self._populating_tasks == 1:
      self.emit('start-populating')
    GLib.idle_add(self._popOnIdle, row_reference)

  def _childrenIndexesInParent(self, accessible):
    '''
    Gets ids from children (either all of them or only those that are not leaves).

    @param accessible: An accessible from which we want to get children ids.
    @type accessible: L{Accessibility.Accessible}

    @return: A list with children ids.
    @rtype: list
    '''

    if not self._hide_leaves:
      return [i for i in range(accessible.childCount)]
    else:
      children_ids = []
      for i in range(accessible.childCount):
        child = accessible.getChildAtIndex(i)
        if child.childCount > 0 or child.getRoleName() != 'application':
          children_ids.append(i)
      return children_ids

  def _selectChild(self, parent, index):
    '''
    Returns a child id.

    @param parent: An accessible from which we want to select a child id.
    @type parent: L{Accessibility.Accessible}
    @param index: An index to retrieve the child id. In some cases, it is equal to the id.
    @type index: integer

    @return: A child id.
    @rtype: integer
    '''

    if not self._hide_leaves:
      return index
    else:
      children = self._childrenIndexesInParent(parent)
      return children[index]

  def children_number(self, parent):
    '''
    Returns how many children an accessible has (either all of them or only those that are not leaves).

    @param parent: An accessible from which we want to get the number of children.
    @type parent: L{Accessibility.Accessible}

    @return: The number of children (including leaves or not) an accessible has.
    @rtype: integer
    '''

    if not self._hide_leaves:
      return parent.childCount
    else:
      children = self._childrenIndexesInParent(parent)
      return len(children)

  def _popOnIdle(self, row_reference):
    '''
    Idle callback for populating the children of a given row reference.
    
    @param row_reference: The parent row reference.
    @type row_reference: gtk.TreeRowReference
    
    @return: False if task is done (to stop handler).
    @rtype: boolean
    '''
    remove_iter = None
    iter = None
    parent = self.desktop

    if row_reference:
      if not row_reference.valid():
        self._endPopTask()
        return False
      iter = self.get_iter(row_reference.get_path())
      parent = self[iter][COL_ACC]
      tree_path = row_reference.get_path()
      path = tuple(tree_path.get_indices())
      if self[path+(0,)][COL_DUMMY]:
        remove_iter = self.iter_children(iter)

    already_populated_num = self.iter_n_children(iter)

    if already_populated_num >= self.children_number(parent) and \
          not remove_iter:
      if iter:
        self[iter][COL_FILLED] = True
      self.emit('row-filled', iter)
      self._endPopTask()
      return False
    elif remove_iter:
      already_populated_num -= 1
    try:
      index = self._selectChild(parent, already_populated_num)
      child = parent.getChildAtIndex(index)
    except LookupError:
      child = None

    row = self._buildRow(child)
    self.append(iter, row)

    if remove_iter:
      self.remove(remove_iter)
    return True

  def _endPopTask(self):
    '''
    Convinience function for stopping a populating task.
    '''
    self._populating_tasks -= 1
    if self._populating_tasks == 0:
      self.emit('end-populating')

  def popToPath(self, path):
    '''
    Populate the model with accessible nodes up to given path.
    
    @param path: Path to populate model to.
    @type path: tuple
    '''
    if not self._walkThroughFilled(path):
      self._path_to_populate = path
    else:
      self.emit('row-filled', self.get_iter(path))
      self._path_to_populate = None

  def _walkThroughFilled(self, path):
    '''
    Reach node in path that is not populated yet, and populate it.
    
    @param path: Path to fill.
    @type path: tuple
    
    @return: True if entire path is populated.
    @rtype: boolean
    '''
    for i in range(1, len(path)):
      if not self[path[:i]][COL_FILLED]:
        self.popLevel(self.get_iter(path[:i]))
        return False
    return True      

  def _onRowFilled(self, model, iter):
    '''
    Callback for "row-filled" signal. If there is a specific path we need to populate,
    we continue populating the next node.
    
    @param model: Model that emitted signal (self).
    @type model: L{AccessibleModel}
    @param iter: Iter of row that has been populated.
    @type iter: gtk.TreeIter
    '''
    if iter and self._path_to_populate:
      tree_path = self.get_path(iter)
      path = tuple(tree_path.get_indices())
      if self._path_to_populate[:len(path)] == path:
        if self._walkThroughFilled(self._path_to_populate):
          self._path_to_populate = None

  def getIndexInParent(self, child):
    '''
    Returns a position of a child in its parent.

    @param child: Accessible for which we want to determine the index.
    @type child: L{Accessibility.Accessible}

    @return: The child's index or -1 if it wasn't found
    @rtype: integer
    '''
    if not self._hide_leaves:
      return child.getIndexInParent()
    else:
      parent = child.parent
      children = self._childrenIndexesInParent(parent)

      for i in children:
        if parent.getChildAtIndex(i) == child:
          return children.index(i)
      return -1

  def getAccPath(self, acc):
    '''
    Get the tree path that a given accessible should have.
    
    I{Note:} The accessible does not necessarily need to be resident in the model.
    
    @param acc: The accessible we want a path of.
    @type acc: L{Accessibility.Accessible}
    
    @return: The path to the accessible.
    @rtype: tuple
    '''
    path = ()
    child = acc
    while child.get_parent():
      try:
        index_in_parent = self.getIndexInParent(child)
        if index_in_parent < 0:
          break
        path = (index_in_parent,) + path
      except Exception as e:
        return None
      child = child.get_parent()
    if not self._hide_leaves:
      try:
        path = (list(self.desktop).index(child),) + path
      except Exception as e:
        return None

    return path

  def _buildRow(self, accessible, dummy=False):
    '''
    Wrapper for building a row in the tree. Use this method instead of trying
    to construct the row by hand as it will be synced with the design of the
    model fields.

    @param accessible: Accessible object
    @type accessible: L{Accessibility.Accessible}
    @param dummy: Is this a dummy row?
    @type dummy: boolean
    '''
    if accessible is not None:
      icon = getIcon(accessible)
      name = accessible.name
      role = accessible.getLocalizedRoleName()
      count = str(accessible.childCount)
    else:
      icon = None
      if not dummy:
        name = _('<dead>')
      else:
        name = None
      role = None
      count = None
    return [icon, name, role, count, False, dummy, accessible]

class AccessibleTreeView(gtk.TreeView, Tools):
  '''
  The treeview for the desktop's accessibles. The treeview's model (L{AccessibleModel}
  is only populated when the treeview is traversed and nodes are expanded. This class
  listens for 'row-expanded' events in order to have a tree node populated. Nodes that
  are selected are updated into the L{Node} instance variable. This treeview also 
  updates automatically in response to at-spi children change events.

  @ivar desktop: The desktop accessible. It holds references to all the 
  application L{Accessibility.Accessible}s
  @type desktop: L{Accessibility.Accessible}
  @ivar node: An object with a reference to the currently selected accessible.
  @type node: L{Node}
  @ivar model: The data model of this treeview.
  @type model: L{AccessibleModel}
  '''
  def __init__(self, node):
    '''
    Initialize the treeview. Build the proper columns.
    Connect all of the proper signal handlers and at-spi event handlers.
    
    @param node: The main application node.
    @type node: L{Node}
    '''
    gtk.TreeView.__init__(self)

    self.desktop = pyatspi.Registry.getDesktop(0)
    self.node = node
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
    tvc.add_attribute(crp, 'pixbuf', COL_ICON)
    tvc.add_attribute(crt, 'text', COL_NAME)
    tvc.set_resizable(True)
    tvc.set_cell_data_func(crt, self._accCellDataFunc)
    tvc.set_cell_data_func(crp, self._accCellDataFunc)
    self.append_column(tvc)
    crt= gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Role'))
    tvc.pack_start(crt, True)
    tvc.add_attribute(crt, 'text', COL_ROLE)
    tvc.set_resizable(True)
    tvc.set_cell_data_func(crt, self._accCellDataFunc)
    self.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Children'))
    tvc.pack_start(crt, True)
    tvc.add_attribute(crt, 'text', COL_CHILDCOUNT)
    tvc.set_resizable(True)
    tvc.set_cell_data_func(crt, self._accCellDataFunc)
    self.append_column(tvc)

    self.model.connect('row-filled', self._onRowFilled)
    self.model.connect('start-populating', self._onStartPop)
    self.model.connect('end-populating', self._onEndPop)
    self._path_to_expand = None

    self._refreshTopLevel()

    selection = self.get_selection()
    selection.unselect_all()
    selection.connect('changed', self._onSelectionChanged)
    selection.set_select_function(self._selectFunc, None)
    self.connect('row-expanded', self._onExpanded)

    pyatspi.Registry.registerEventListener(self._accEventChildChanged, 
                                           'object:children-changed')

    pyatspi.Registry.registerEventListener(
        self._accEventNameChanged, 
        'object:property-change:accessible-name')

    self.action_group = gtk.ActionGroup.new('TreeActions')
    self.action_group.add_toggle_actions(
      [('HideShowLeaves', None, _('_Hide/Show Applications without children'), None,
        None, self._onHideShowLeaves, False)])
    self.action_group.add_actions([
        ('RefreshAll', gtk.STOCK_REFRESH, _('_Refresh Registry'),
        # Translators: Appears as tooltip
        #
         None, _('Refresh all'), self._refreshTopLevel),
        # Translators: Refresh current tree node's children.
        #
        ('RefreshCurrent', gtk.STOCK_JUMP_TO, _('Refresh _Node'),
        # Translators: Appears as tooltip
        #
         None, _('Refresh selected node\'s children'), 
         self._refreshCurrentLevel)])  

    self.refresh_current_action = self.action_group.get_action('RefreshCurrent')
    self.refresh_current_action.set_sensitive(False)

    self.connect('popup-menu', self._onPopup)
    self.connect('button-press-event', self._onPopup)

    self.connect('cursor-changed', self._onCursorChanged)

  def _onCursorChanged(self, tree):
    '''
    Set sensitivity of refresh function only if the tree cursor is 
    on an accessible.
    '''
    path = self.get_cursor()[0]
    self.refresh_current_action.set_sensitive(path is not None)      

  def _onPopup(self, w, event=None):
    '''
    Callback for popup button or right mouse button. Brings up a context
    menu.
    '''
    if event:
      if event.button != 3:
        return False
      path = self.get_path_at_pos(int(event.x), int(event.y))[0]
      selection = self.get_selection()
      selection.set_mode(gtk.SelectionMode.NONE)
      self.set_cursor(path, None, False)
      selection.set_mode(gtk.SelectionMode.SINGLE)      
      time = event.time
      button = event.button
      func = None
      extra_data = None
    else:
      path, col= self.get_cursor()
      time = gtk.get_current_event_time()
      button = 0
      extra_data = getTreePathBoundingBox(self, path, col)
      func = lambda m, b: (b.x, b.y + (b.height/2), True)
      
    menu = ui_manager.uimanager.get_widget(ui_manager.POPUP_MENU_PATH)
    menu.popup(None, None, func, extra_data, button, time)
    return True

  def _refreshTopLevel(self, action=None, data=None):
    '''
    Refreshes the entire tree at the desktop level.

    @param action: Action object that emitted this signal, if any.
    @type: gtk.Action
    '''
    self.model.clear()
    self.model.popLevel(None)
    # iter over all apps in the desktop too
    
  def _refreshCurrentLevel(self, action, data=None):
    '''
    Refreshes the current level. Selects and expands the parent of the level.

    @param action: Action object that emitted this signal, if any.
    @type: gtk.Action
    '''
    path = self.get_cursor()[0]
    if path == None: return
    is_expanded = self.row_expanded(path)
    self._refreshChildren(self.model.get_iter(path))
    if is_expanded:
      self.expand_row(path, False)
      self._onExpanded(self, self.model.get_iter(path), path)

  def _onHideShowLeaves(self, option):
    '''
    Hides/Shows all leaves (accessibles with no children) from the accessible treeview.
    '''

    self.model._hideShowLeaves()
    self._refreshTopLevel()

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
    acc = self.model[iter][COL_ACC]
    # populate this level
    self.model.popLevel(iter)

  def _accEventNameChanged(self, event):
    '''
    Event handler for "object:property-change:accessible-name". 
    Updates the treeview accordingly.
    
    @param event: The event which triggered this handler.
    @type event: L{pyatspi.event.Event}
    '''
    if self.isMyApp(event.source) or event.source == self.desktop:
      # Bad karma
      return
    if self.model.isInModel(event.source):
      try:
        path = self.model.getAccPath(event.source)
        iter = self.model.get_iter(path)
      except:
          pass
      else:
          self.model[iter][COL_NAME] = event.source.name

  def _accEventChildChanged(self, event):
    '''
    Event handler for "object:children-changed". Updates the treeview accordingly.
    
    @param event: The event which triggered this handler.
    @type event: L{pyatspi.event.Event}
    '''
    if self.isMyApp(event.source):
      # Bad karma
      return
    if self.model.isInModel(event.source):
      try:
        path = self.model.getAccPath(event.source)
        iter = self.model.get_iter(path)
      except:
        iter = None
        path = None
      if (event.source == self.desktop) or \
            (path and self.model[path][COL_FILLED]):
        if event.type.minor == 'add':
          self._addChild(iter, event.source)
        elif event.type.minor == 'remove':
          self._removeChild(iter, event.source)
      if iter and self.model.iter_is_valid(iter):
        self.model[iter][COL_CHILDCOUNT] = str(event.source.childCount)

  def removeLeaves(self, accessibles):
    '''
    Removes accessibles with no children (leaves) from a list
    of accessibles. 

    @param accessibles: List of accessibles to be examined
    @type accessibles: list

    @return: The accessibles list without leaves
    @rtype: list
    '''

    nonleaves = []
    for acc in accessibles:
      if acc.childCount > 0:
        nonleaves.append(acc)
    return nonleaves

  def _addChild(self, iter, parent):
    '''
    Add the new child to the given accessible.

    @param iter: Th iter of the row that needs a child added. 
    @type iter: L{gtk.TreeIter}
    @param parent: The given row's accessible.
    @type parent: L{Accessibility.Accessible}
    '''
    old_children = self.model.getChildrenAccs(iter)
    new_children = list(parent) 
    if self.model.getHideLeaves():
      # time for new child load its children (if it has any),
      # so it won't be confused with a leaf
      sleep(ACCESSIBLE_LOADING)
      new_children = self.removeLeaves(new_children)

    old_children = set(old_children)
    new_children = set(new_children)

    added = new_children.difference(old_children)
    try:
      new_child = added.pop()
    except KeyError:
      return
    row = self.model._buildRow(new_child)
    if new_child is None:
      self.model.append(iter, row)
    else:
      self.model.insert(iter, self.model.getIndexInParent(new_child), row)
      # We do this because an application won't have an icon loaded in 
      # the window manager when it is first registered to at-spi
      if new_child == new_child.getApplication():
        GLib.timeout_add(1000, self._refreshIcon, new_child)
    
  def _refreshIcon(self, app):
    '''
    Refresh the icon of a given application's accessible. This is done because it
    takes wnck a while to load an application's icon at application startup.

    @param app: The given application's accessible.
    @type app: L{Accessibility.Accessible}
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
    @type parent: L{Accessibility.Accessible}
    '''
    if parent_iter:
      iter = self.model.iter_children(parent_iter)
    else:
      iter = self.model.get_iter_first()
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
      self._refreshTopLevel()
      return
    child_iter = self.model.iter_children(iter)
    while child_iter:
      if not self.model.remove(child_iter):
        break
    acc = self.model[iter][COL_ACC]
    self.model[iter][COL_CHILDCOUNT] = str(acc.childCount)
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
    self._path_to_expand = None
    model, iter = selection.get_selected()
    if iter:
      new_acc = model[iter][COL_ACC]
    else:
      new_acc = self.desktop
    if new_acc == self.node.acc:
      return
    self.node.handler_block(self._changed_handler)
    self.node.update(new_acc)
    self.node.handler_unblock(self._changed_handler)
    if iter:
      tree_path = model.get_path(iter)
      path = tuple(tree_path.get_indices())

      self.node.tree_path = list(path[1:])

  def _onAccChanged(self, node, acc):
    '''
    Change the treeview's selection to the updated accessible in the L{Node}.

    @param node: The L{node} that emitted the signal.
    @type node: L{Node}
    @param acc: The new accessible in the node.
    @type acc: L{Accessibility.Accessible}
    '''
    if self.isMyApp(acc):
      # Bad karma
      return
    path = self.model.getAccPath(acc)
    if not path:
      return
    if len(path) >= 1:
      self.selectNodeAtPath(path)
      self.node.tree_path = list(path[1:])

  def selectNodeAtPath(self, path):
    '''
    Select the node at the current path. The path does not need to exist in the model,
    only in the accessibles tree. The model will get populated accordingly.

    @param path: The path to select.
    @type path: tuple
    '''
    try:
      dummy = self.model[path][COL_DUMMY]
    except:
      dummy = True
    if dummy:
      self._path_to_expand = path
      self.model.popToPath(path)
    else:
      self._selectExistingPath(path)

  def _onRowFilled(self, model, iter):
    '''
    Callback for "row-filled" (populated) signal. Used for selecting a child node in 
    the given iter if L{selectNodeAtPath} was called on one of the given 
    iter's children.
    
    @param model: Model that emitted this signal.
    @type model: L{AccessibleModel}
    @param iter: Iter of row that was populated with children.
    @type iter: gtk.TreeIter
    '''
    if iter and self._path_to_expand and \
          self._path_to_expand[:-1] == model.get_path(iter).get_indices():
      self._selectExistingPath(self._path_to_expand)
      self._path_to_expand = None

  def _selectExistingPath(self, path):
    '''
    Select a path that already exists. Expand, scroll, and select.
    
    @param path: Path to select.
    @type path: tuple
    '''
    tree_path = gtk.TreePath(path[:-1])
    if len(path) > 1:
      self.expand_to_path(tree_path)
    self.scroll_to_cell(path)
    selection = self.get_selection()
    selection.select_path(path)
    

  def _onStartPop(self, model):
    '''
    Callback for when the model is populating, changes the cursor to a watch.
    
    @param model: Model that emitted the signal.
    @type model: L{AccessibleModel}
    '''
    if self.get_window():
      window = self.get_window()
      window.set_cursor(gdk.Cursor(gdk.CursorType.WATCH))

  def _onEndPop(self, model):
    '''
    Callback for when the model stops populating, changes the cursor to an arrow.
    
    @param model: Model that emitted the signal.
    @type model: L{AccessibleModel}
    '''
    if self.get_window():
      window = self.get_window()
      window.set_cursor(gdk.Cursor(gdk.CursorType.TOP_LEFT_ARROW))

  def _accCellDataFunc(self, tvc, cellrenderer, model, iter_id, iter_type):
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
    # TODO: Remove idle_add when at-spi2 reentrancy issues are fixed
    GLib.idle_add(self._accCellDataFuncReal, tvc, cellrenderer, model, iter_id)

  def _accCellDataFuncReal(self, tvc, cellrenderer, model, iter_id):
    '''
    Called by _acCellDataFunc when idle

    @param tvc: A treeview column.
    @type tvc: L{gtk.TreeViewColumn}
    @param cellrenderer: The cellrenderer that needs to be tweaked.
    @type cellrenderer: L{gtk.CellRenderer}
    @param model: The treeview's data model.
    @type model: L{AccessibleModel}
    @param iter: The iter at the given row.
    @type iter: L{gtk.TreeIter}
    '''
    if model.iter_is_valid(iter_id):
      acc = model.get_value(iter_id, COL_ACC)
    else:
      acc = None
    if self.isMyApp(acc):
      cellrenderer.set_property('sensitive', False)
    else:
      cellrenderer.set_property('sensitive', True)

  def _selectFunc(self, tree_selection, acc_model, tree_path, foo3, foo4):
    '''
    A selection function. Does not allow his application's node to be selected.

    @param path: The path to the selected row.
    @type path: tuple

    @return: True if the row's accessible is not this app.
    @rtype: boolean
    '''
    path = tuple(tree_path.get_indices())

    acc = self.model[path][COL_ACC]
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
    self.node.highlight()
