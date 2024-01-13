from gi.repository import GLib
from gi.repository import Gio as gio
from gi.repository import Gtk as gtk
from gi.repository import Atk as atk

import os
from xml.dom.minidom import getDOMImplementation, parse, Element
from .i18n import _
from pyatspi import getPath
from random import random
import random
from . import menus

COL_NAME = 0
COL_APP = 1
COL_PATH = 2
_BM_ATTRIBS = ['title', 'app', 'path']

BOOKMARKS_PATH = os.path.join(GLib.get_user_config_dir(), 'accerciser')
BOOKMARKS_FILE = 'bookmarks.xml'

class BookmarkStore(gtk.ListStore):
  '''
  Bookmark manager class. Does three things:
  1. Stores bookmarks.
  2. Persists bookmark changes to disk.
  3. Keeps bookmarks submenu up to date.

  @ivar application: The accerciser application.
  @type application: gtk.Application
  @ivar node: Main application's node.
  @type node: L{Node}
  @ivar _xmldoc: XML documenr object.
  @type _xmldoc: xml.dom.DOMImplementation
  '''
  def __init__(self, node, application, window):
    '''
    Initialize bookmark manager. Load saved bookmarks from disk.

    @param node: Main application's node.
    @type node: L{Node>
    @ivar application: The accerciser application.
    @type application: gtk.Application
    '''
    gtk.ListStore.__init__(self, object)
    self.application = application
    self._buildMenuUI()
    self.node = node
    self.parent_window = window
    bookmarks_fn = os.path.join(BOOKMARKS_PATH, BOOKMARKS_FILE)
    try:
      self._xmldoc = parse(bookmarks_fn)
    except:
      impl = getDOMImplementation()
      self._xmldoc = impl.createDocument(None, "bookmarks", None)
    self._cleanDoc()
    self._populateModel()
    self.connect('row-changed', self._onRowChanged)
    self.connect('row-deleted', self._onRowDeleted)
    self.connect('row-inserted', self._onRowInserted)

  def _buildMenuUI(self):
    '''
    Build's the initial submenu with functionality menu items.
    '''
    menu_items = [
      (menus.bookmarks_menu_general_section, 'add_bookmark', 'list-add',
        _('_Add Bookmark…'), '<Control>d', self._onAddBookmark),
      (menus.bookmarks_menu_general_section,  'edit_bookmarks', 'document-edit',
        _('_Edit Bookmarks…'), None, self._onEditBookmarks)]
    self.application.addMenuItems(menu_items)

  def _onAddBookmark(self, action, data=None):
    '''
    Callback for AddBookmark action.

    @param action: Action that emitted this signal.
    @type action: gio.Action
    '''
    iter = self.bookmarkCurrent()
    if not iter: return
    bookmark = self[iter][0]
    dialog = self._NewBookmarkDialog(bookmark, self.parent_window)
    response_id = dialog.run()
    if response_id == gtk.ResponseType.OK:
      bookmark.title, bookmark.app, bookmark.path = dialog.getFields()
    else:
      self.removeBookmark(bookmark)
    dialog.destroy()

  def _onEditBookmarks(self, action, data=None):
    '''
    Callback for EditBookmark action.

    @param action: Action that emitted this signal.
    @type action: gio.Action
    '''
    dialog = self._EditDialog(self)
    dialog.show()

  def _cleanDoc(self):
    '''
    Clean up whitespace in XML doc.
    '''
    elements = self._getElements()
    for node in self._xmldoc.documentElement.childNodes:
      if node not in elements:
        self._xmldoc.documentElement.removeChild(node)

  def _populateModel(self):
    '''
    Populate model with stored bookmarks.
    '''
    for node in self._getElements():
      title = node.getAttribute('title')
      app = node.getAttribute('app')
      path = node.getAttribute('path')
      self.addBookmark(title, app, path)

  def addBookmark(self, title, app, path):
    '''
    Add a bookmark to the maanger.

    @param title: Title of bookmark
    @type title: string
    @param app: Application name of bookmark.
    @type app: string
    @param path: Path of bookmarks.
    @type path: string

    @return: Tree iter of new bookmark.
    @rtype: gtk.TreeIter
    '''
    iter = self.append([None])
    bookmark = self._Bookmark(self, title, app, path, self.application)
    self[iter][0] = bookmark
    return iter

  def removeBookmark(self, bookmark):
    '''
    Remove bookmark from manager.

    @param bookmark: Bookmark to remove.
    @type bookmark: BookmarkStore._Bookmark
    '''
    bookmark.removeSelf()
    for row in self:
      if row[0] == bookmark:
        self.remove(row.iter)

  def _onBookmarkChanged(self, bookmark):
    '''
    Emit a 'row-changed' signal when bookmark's properties change.

    @param bookmark: Bookmark whose properties changed.
    @type bookmark: L{BookmarkStore._Bookmark}
    '''
    for row in self:
      if row[0] == bookmark:
        self.row_changed(row.path, row.iter)

  def _getElements(self):
    '''
    Get a list of elements from XML doc. Filter out strings.

    @return: list of elements.
    @rtype: list of Element
    '''
    return [x for x in self._xmldoc.documentElement.childNodes if isinstance(x, Element)]

  def _onRowChanged(self, model, tree_path, iter):
    '''
    Callback for row changes. Persist changes to disk.

    @param model: Model that emitted signal
    @type model: L{BookmarkStore}
    @param path: Path of row that changed.
    @type path: tuple
    @param iter: Iter of row that changed.
    @type iter: gtk.TreeIter
    '''
    path = tuple(tree_path.get_indices())
    node = self._getElements()[path[0]]
    bookmark = model[iter][0]
    if bookmark is None: return
    for attr in _BM_ATTRIBS:
      if getattr(bookmark, attr) is None: continue
      node.setAttribute(attr, getattr(bookmark, attr))
    self._persist()

  def _onRowDeleted(self, model, tree_path):
    '''
    Callback for row deletions. Persist changes to disk, and update UI.

    @param model: Model that emitted signal
    @type model: L{BookmarkStore}
    @param path: Path of row that got deleted.
    @type path: tuple
    '''
    path = tuple(tree_path.get_indices())
    node = self._getElements()[path[0]]
    self._xmldoc.documentElement.removeChild(node)
    self._persist()

  def _onRowInserted(self, model, path, iter):
    '''
    Callback for row insertions. Persist changes to disk.

    @param model: Model that emitted signal
    @type model: L{BookmarkStore}
    @param path: Path of row that is inserted.
    @type path: tuple
    @param iter: Iter of row that is inserted.
    @type iter: gtk.TreeIter
    '''
    node = self._xmldoc.createElement('bookmark')
    self._xmldoc.documentElement.appendChild(node)
    self._persist()

  def _persist(self):
    '''
    Persist DOM to disk.
    '''
    bookmarks_fn = os.path.join(BOOKMARKS_PATH, BOOKMARKS_FILE)
    try:
      if not os.path.exists(os.path.dirname(bookmarks_fn)):
        os.mkdir(os.path.dirname(bookmarks_fn))
      f = open(bookmarks_fn, 'w')
    except:
      return
    self._xmldoc.writexml(f, '', '  ', '\n')
    f.close()

  def _onBookmarkActivate(self, bookmark):
    '''
    Bookmark activation callback

    @param bookmark: Bookmark that was activated.
    @type bookmark: L{BookmarkStore._Bookmark}
    '''
    self.jumpTo(bookmark)

  def jumpTo(self, bookmark):
    '''
    Go to bookmarks.

    @param bookmark: Bookmark to go to.
    @type bookmark: L{BookmarkStore._Bookmark}
    '''
    if '' == bookmark.path:
      path = ()
    else:
      path = list(map(int, bookmark.path.split(',')))
    self.node.updateToPath(bookmark.app, path)

  def bookmarkCurrent(self):
    '''
    Bookmark the currently selected application-wide node.

    @return: Tree iter of new bookmark.
    @rtype: gtk.TreeIter
    '''
    if self.node.acc in (self.node.desktop, None): return None
    if self.node.tree_path is not None:
      path = ','.join(map(str, self.node.tree_path))
    else:
      path = ','.join(map(str, getPath(self.node.acc)))
    app = self.node.acc.getApplication()
    role = self.node.acc.getLocalizedRoleName()
    first_bm_name = '%s in %s' % (self.node.acc.name or role, app.name)
    bm_name = first_bm_name
    i = 1
    while self._nameIsTaken(bm_name):
      bm_name = '%s (%d)' % (first_bm_name, i)
      i += 1
    return self.addBookmark(bm_name, app.name, path)

  def _nameIsTaken(self, name):
    '''
    Check if label text is already in use.

    @param name: Name to check.
    @type name: string

    @return: True is name is taken.
    @rtype: boolean
    '''
    for row in self:
      bookmark = row[0]
      if bookmark.title == name:
        return True
    return False

  class _EditDialog(gtk.Dialog):
    '''
    Dialog for editing and managing bookmarks.
    '''
    def __init__(self, bookmarks_store):
      '''
      Initialize dialog.

      @param bookmarks_store: Bookmarks manager.
      @type bookmarks_store: L{BookmarkStore}
      '''
      gtk.Dialog.__init__(self, name=_('Edit Bookmarks…'))
      close_button = self.add_button(_("_Close"), gtk.ResponseType.CLOSE)
      close_button.set_image(gtk.Image.new_from_icon_name("window-close", gtk.IconSize.BUTTON))
      self.set_default_size(480, 240)
      self.connect('response', self._onResponse)
      vbox = self.get_children()[0]
      hbox = gtk.Box()
      hbox.set_spacing(3)
      tv = self._createTreeView(bookmarks_store)
      sw = gtk.ScrolledWindow()
      sw.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
      sw.set_shadow_type(gtk.ShadowType.IN)
      sw.add(tv)
      hbox.pack_start(sw, True, True, 0)
      button_vbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)
      hbox.pack_start(button_vbox, False, False, 0)
      add_button = gtk.Button.new_with_mnemonic(_('_Add'))
      add_button.set_image(gtk.Image.new_from_icon_name("list-add", gtk.IconSize.BUTTON))
      add_button.connect('clicked', self._onAddClicked, tv)
      remove_button = gtk.Button.new_with_mnemonic(_('_Remove'))
      remove_button.set_image(gtk.Image.new_from_icon_name("list-remove", gtk.IconSize.BUTTON))
      remove_button.connect('clicked', self._onRemoveClicked, tv)
      jump_button = gtk.Button.new_with_mnemonic(_('_Jump to'))
      jump_button.set_image(gtk.Image.new_from_icon_name("go-jump", gtk.IconSize.BUTTON))
      jump_button.connect('clicked', self._onJumpToClicked, tv)
      button_vbox.pack_start(add_button, False, False, 0)
      button_vbox.pack_start(remove_button, False, False, 0)
      button_vbox.pack_start(jump_button, False, False, 0)
      vbox.pack_start(hbox, True, True, 0)
      hbox.set_border_width(3)
      self.set_transient_for(bookmarks_store.parent_window)
      self.show_all()

    def _onAddClicked(self, button, tv):
      '''
      Callback for add button. Add a bookmark.

      @param button: Add button
      @type button: gtk.Button
      @param tv: Treeview of dialog.
      @type tv: gtk.TreeView
      '''
      model = tv.get_model()
      iter = model.bookmarkCurrent()
      if not iter: return
      selection = tv.get_selection()
      selection.select_iter(iter)

    def _onRemoveClicked(self, button, tv):
      '''
      Callback for remove button. Remove a bookmark.

      @param button: Remove button
      @type button: gtk.Button
      @param tv: Treeview of dialog.
      @type tv: gtk.TreeView
      '''
      selection = tv.get_selection()
      model, iter = selection.get_selected()
      path = model.get_path(iter)
      if iter:
        bookmark = model[iter][0]
        model.removeBookmark(bookmark)
        selection.select_path(0)


    def _onJumpToClicked(self, button, tv):
      '''
      Callback for "jump to" button. Go to bookmark.

      @param button: "jump to" button
      @type button: gtk.Button
      @param tv: Treeview of dialog.
      @type tv: gtk.TreeView
      '''
      selection = tv.get_selection()
      model, iter = selection.get_selected()
      bookmark = model[iter][0]
      model.jumpTo(bookmark)

    def _onResponse(self, dialog, response):
      '''
      Callback for dialog response.

      @param dialog: Dialog.
      @type dialog: gtk.Dialog
      @param response: response ID.
      @type response: integer
      '''
      self.destroy()

    def _createTreeView(self, model):
      '''
      Create dialog's tree view.

      @param model: Data model for view.
      @type model: L{BookmarkStore}

      @return: The new tree view.
      @rtype: gtk.TreeView
      '''
      tv = gtk.TreeView()
      tv.set_model(model)

      crt = gtk.CellRendererText()
      crt.set_property('editable', True)
      crt.connect('edited', self._onCellEdited, model, COL_NAME)
      tvc = gtk.TreeViewColumn(_('Title'))
      tvc.pack_start(crt, True)
      tvc.set_cell_data_func(crt, self._cellDataFunc, COL_NAME)
      tv.append_column(tvc)

      crt = gtk.CellRendererText()
      crt.set_property('editable', True)
      crt.connect('edited', self._onCellEdited, model, COL_APP)
      tvc = gtk.TreeViewColumn(_('Application'))
      tvc.pack_start(crt, True)
      tvc.set_cell_data_func(crt, self._cellDataFunc, COL_APP)
      tv.append_column(tvc)

      crt = gtk.CellRendererText()
      crt.set_property('editable', True)
      crt.connect('edited', self._onCellEdited, model, COL_PATH)
      tvc = gtk.TreeViewColumn(_('Path'))
      tvc.pack_start(crt, True)
      tvc.set_cell_data_func(crt, self._cellDataFunc, COL_PATH)
      tv.append_column(tvc)

      return tv

    def _onCellEdited(self, cellrenderer, path, new_text, model, col_id):
      '''
      Callback for cell editing. Blocks unallowed input.

      @param cellrenderer: Cellrenderer that is being edited.
      @type cellrenderer: gtk.CellRendererText
      @param path: Path of tree node.
      @type path: tuple
      @param new_text: New text that was entered.
      @type new_text: string.
      @param model: Model of tree view.
      @type model: L{BookmarkStore}
      @param col_id: Column ID of change.
      @type col_id: integer
      '''
      if col_id == COL_NAME and new_text == '':
        return
      if col_id == COL_PATH:
        try:
          int_path = list(map(int, new_text.split(',')))
        except ValueError:
          return
      bookmark = model[path][0]
      setattr(bookmark, _BM_ATTRIBS[col_id], new_text)

    def _cellDataFunc(self, column, cell, model, iter, col_id):
      '''
      Cell renderer display function.

      @param column: Tree view column
      @type column: gtk.TreeViewColumn
      @param cell: Cell renderer.
      @type cell: gtk.CellRendererText
      @param model: Data model.
      @type model: L{BookmarkStore}
      @param iter: Tree iter.
      @type iter: gtk.TreeIter
      @param col_id: Column ID.
      @type col_id: integer
      '''
      bookmark = model[iter][0]
      cell.set_property('text',
                        getattr(bookmark, _BM_ATTRIBS[col_id], ''))

  class _NewBookmarkDialog(gtk.Dialog):
    '''
    New bookmark entry dialog.

    @ivar _title_entry: Title entry widget
    @type _title_entry: gtk.Entry
    @ivar _app_entry: Application name entry widget
    @type _app_entry: gtk.Entry
    @ivar _path_entry: Path entry widget
    @type _path_entry: gtk.Entry
    '''
    def __init__(self, bookmark, parent_window):
      '''
      Initialize the dialog.

      @param bookmark: New bookmark to edit.
      @type bookmark: L{BookmarkStore._Bookmark}
      '''
      gtk.Dialog.__init__(self, _('Add Bookmark…'))
      cancel_button = self.add_button("_Cancel", gtk.ResponseType.CANCEL)
      cancel_button.set_image(gtk.Image.new_from_icon_name("gtk-cancel", gtk.IconSize.BUTTON))
      ok_button = self.add_button("_Add", gtk.ResponseType.OK)
      ok_button.set_image(gtk.Image.new_from_icon_name("list-add", gtk.IconSize.BUTTON))
      ok_button.set_sensitive(False)
      self.set_default_response(gtk.ResponseType.OK)
      grid = gtk.Grid()
      grid.set_row_spacing(3)
      grid.set_column_spacing(3)
      vbox = self.get_children()[0]
      vbox.add(grid)
      self._title_entry = gtk.Entry()
      self._title_entry.connect('changed', self._onChanged, ok_button)
      self._app_entry = gtk.Entry()
      self._path_entry = gtk.Entry()
      for i, label_entry_pair in enumerate([(_('Title:'),
                                             bookmark.title,
                                            self._title_entry),
                                           (_('Application:'),
                                             bookmark.app,
                                            self._app_entry),
                                           (_('Path:'),
                                             bookmark.path,
                                            self._path_entry)]):
        label, value, entry = label_entry_pair
        entry.set_text(value)
        entry.connect('activate', self._onEnter, ok_button)
        label_widget = gtk.Label.new(label)
        label_widget.set_alignment(0.0, 0.5)
        label_acc = label_widget.get_accessible()
        entry_acc = entry.get_accessible()
        label_acc.add_relationship(atk.RelationType.LABEL_FOR, entry_acc)
        entry_acc.add_relationship(atk.RelationType.LABELLED_BY, label_acc)
        grid.attach(gtk.Label.new(label), 0, i, 1, 1)
        grid.attach(entry, 1, i, 1, 1)
      self.set_transient_for(parent_window)
      self.show_all()

    def _onChanged(self, entry, button):
      '''
      Title entry changed callback. If title entry is empty, disable "add" button.

      @param entry: Entry widget that changed.
      @type entry: gtk.Entry
      @param button: Add button.
      @type button: gtk.Button
      '''
      text = entry.get_text()
      not_empty = bool(text)
      button.set_sensitive(not_empty)

    def _onEnter(self, entry, button):
      '''
      Finish dialog when enter is pressed.

      @param entry: Entry widget that changed.
      @type entry: gtk.Entry
      @param button: Add button.
      @type button: gtk.Button
      '''
      button.clicked()

    def getFields(self):
      '''
      Return value of all fields.

      @return: title, app name, and path.
      @rtype: tuple
      '''
      return \
          self._title_entry.get_text(), \
          self._app_entry.get_text(), \
          self._path_entry.get_text()

  class _Bookmark:
    '''
    Bookmark object.

    @ivar bookmark_store: The bookmark store managing this bookmark.
    @type bookmark_store: BookmarkStore
    @ivar title: Bookmark title (and label).
    @type title: string
    @ivar app: Application name.
    @type app: string
    @ivar path: Accessible path.
    @type path: string
    @ivar bookmark_name: Name of the bookmark.
    @type bookmark_name: string
    @ivar accerciser_app: The accerciser application.
    @type accerciser_app: gtk.Application
    @ivar menu_item: The menu item for this bookmark.
    @type menu_item: gio.MenuItem
    '''
    def __init__(self, bookmark_store, title, app, path, accerciser_app):
      '''
      Initialize bookmark.

      @param bookmark_store: The bookmark store managing this bookmark.
      @type bookmark_store: BookmarkStore
      @param title: Bookmark title (and label).
      @type title: string
      @param app: Application name.
      @type app: string
      @param path: Accessible path.
      @type path: string
      @param accerciser_app: The accerciser application.
      @type accerciser_app: gtk.Application
      '''
      self.accerciser_app = accerciser_app
      # find an unused bookmark/action ID/name
      id = 0
      self.bookmark_name = f'bookmark{id}'
      while self.accerciser_app.lookup_action(self.bookmark_name):
        id = id +1
        self.bookmark_name = f'bookmark{id}'

      action_name = 'app.' + self.bookmark_name
      self.menu_item = gio.MenuItem.new(title, action_name)
      menus.bookmarks_menu_individual_section.append_item(self.menu_item)
      action = gio.SimpleAction.new(self.bookmark_name, None)
      action.connect('activate', self._onActivate)
      self.accerciser_app.add_action(action)
      self.bookmark_store = bookmark_store
      self._title = title
      self._app = app
      self._path = path

    def _getTitle(self):
      return self._title
    def _setTitle(self, title):
      self._title = title
      self.menu_item.set_attribute_value('label', GLib.Variant.new_string(title))
      # When inserted into the menu, the menu item's data were just copied, so updating
      # the menu item by itself wouldn't have any effect in the actual menu.
      # Therefore, remove the current entry and insert anew.
      index = self.getMenuItemIndex()
      menus.bookmarks_menu_individual_section.remove(index)
      menus.bookmarks_menu_individual_section.insert_item(index, self.menu_item)
      self.bookmark_store._onBookmarkChanged(self)
    title = property(_getTitle, _setTitle)

    def _getApp(self):
      return self._app
    def _setApp(self, app):
      self._app = app
      self.bookmark_store._onBookmarkChanged(self)
    app = property(_getApp, _setApp)

    def _getPath(self):
      return self._path
    def _setPath(self, path):
      self._path = path
      self.bookmark_store._onBookmarkChanged(self)
    path = property(_getPath, _setPath)

    def _onActivate(self, obj, data=None):
      self.bookmark_store._onBookmarkActivate(self)

    def getMenuItemIndex(self):
      '''
      Return the index that the bookmark's menu entry has in the menu.
      '''
      # iterate over the menu items to find the right one (match by action name)
      index = -1
      for i in range(0, menus.bookmarks_menu_individual_section.get_n_items()):
        action_name = menus.bookmarks_menu_individual_section.get_item_attribute_value(i, 'action', None).get_string()
        if action_name == 'app.' + self.bookmark_name:
          index = i
          break

      assert(index >= 0)
      return index

    def removeSelf(self):
      '''
      Remove the bookmark's menu entry and action.
      '''
      # remove menu item from menu and remove the action
      index = self.getMenuItemIndex()
      menus.bookmarks_menu_individual_section.remove(index)
      self.accerciser_app.remove_action(self.bookmark_name)
