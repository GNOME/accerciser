import gtk, atk, os
from xml.dom.minidom import getDOMImplementation, parse, Element
from i18n import _
from pyatspi import getPath
from random import random
import random
import gobject

COL_NAME = 0
COL_APP = 1
COL_PATH = 2
_BM_ATTRIBS = ['title', 'app', 'path']

BOOKMARKS_PATH = os.path.join(os.environ['HOME'], '.accerciser')
BOOKMARKS_FILE = 'bookmarks.xml'

class BookmarkStore(gtk.ListStore):
  '''
  Bookmark manager class. Does three things:
  1. Stores bookmarks.
  2. Persists bookmark changes to disk.
  3. Keeps bookmarks submenu up to date.

  @ivar _uimanager: Main application UIManager.
  @type _uimanager: gtk.UIManager
  @ivar _bookmarks_action_group: Bookmarks' action group.
  @type _bookmarks_action_group: gtk.ActionGroup
  @ivar node: Main application's node.
  @type node: L{Node}
  @ivar _xmldoc: XML documenr object.
  @type _xmldoc: xml.dom.DOMImplementation
  '''
  def __init__(self, node, uimanager):
    '''
    Initialize bookmark manager. Load saved bookmarks from disk.
    
    @param node: Main application's node.
    @type node: L{Node>
    @param uimanager: Main application UIManager.
    @type uimanager: gtk.UIManager
    '''
    gtk.ListStore.__init__(self, object)
    self._uimanager = uimanager
    self._bookmarks_action_group = gtk.ActionGroup('BookmarkActions')
    self._uimanager.insert_action_group(self._bookmarks_action_group, 0)
    self._buildMenuUI()
    self.node = node
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
    self._bookmarks_action_group.add_actions(
      [('AddBookmark', gtk.STOCK_ADD, 
        _('_Add Bookmark...'), '<Control>d',
        _('Bookmark selected accessible.'), self._onAddBookmark),
       ('EditBookmarks', gtk.STOCK_EDIT, 
        _('_Edit Bookmarks...'), None,
        _('Manage bookmarks.'), self._onEditBookmarks)])


    for action in self._bookmarks_action_group.list_actions():
      merge_id = self._uimanager.new_merge_id()
      action_name = action.get_name()
      self._uimanager.add_ui(merge_id, '/MainMenuBar/Bookmarks', 
                            action_name, action_name, 
                            gtk.UI_MANAGER_MENUITEM, False)

    self._uimanager.add_ui(self._uimanager.new_merge_id(), 
                           '/MainMenuBar/Bookmarks', 
                           'sep', None, 
                           gtk.UI_MANAGER_SEPARATOR, False)

  def _onAddBookmark(self, action):
    '''
    Callback for AddBookmark action.
    
    @param action: Action that emitted this signal.
    @type action: gtk.Action
    '''
    iter = self.bookmarkCurrent()
    if not iter: return
    bookmark = self[iter][0]
    dialog = self._NewBookmarkDialog(bookmark)
    response_id = dialog.run()
    if response_id == gtk.RESPONSE_OK:
      bookmark.title, bookmark.app, bookmark.path = dialog.getFields()
    else:
      self.remove(iter)
    dialog.destroy()

  def _onEditBookmarks(self, action):
    '''
    Callback for EditBookmark action.
    
    @param action: Action that emitted this signal.
    @type action: gtk.Action
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
    name = 'Bookmark%s' % str(self.get_path(iter)[0])
    merge_id = self._uimanager.new_merge_id()
    bookmark = self._Bookmark(name, title, app, path, merge_id)
    bookmark.connect('activate', self._onBookmarkActivate)
    bookmark.connect('notify', self._onBookmarkChanged)
    self._bookmarks_action_group.add_action(bookmark)
    self._uimanager.add_ui(merge_id, 
                           '/MainMenuBar/Bookmarks', name, name, 
                           gtk.UI_MANAGER_MENUITEM, False)
    self[iter][0] = bookmark
    return iter

  def _onBookmarkChanged(self, bookmark, property):
    '''
    Emit a 'row-changed' signal when bookmark's properties emit a 'notify' event.
    
    @param bookmark: Bookmark that emitted 'notify' event.
    @type bookmark: L{BookmarkStore._Bookmark}
    @param property: Property that changed, ignored because we emit dummy signals.
    @type property: Property
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
    return filter(lambda x: isinstance(x, Element),
                  self._xmldoc.documentElement.childNodes)

  def _onRowChanged(self, model, path, iter):
    '''
    Callback for row changes. Persist changes to disk.
    
    @param model: Model that emitted signal
    @type model: L{BookmarkStore}
    @param path: Path of row that changed.
    @type path: tuple
    @param iter: Iter of row that changed.
    @type iter: gtk.TreeIter
    '''
    node = self._getElements()[path[0]]
    bookmark = model[iter][0]
    if bookmark is None: return
    for attr in _BM_ATTRIBS:
      if getattr(bookmark, attr) is None: continue
      node.setAttribute(attr, getattr(bookmark, attr))
    self._persist()

  def _onRowDeleted(self, model, path):
    '''
    Callback for row deletions. Persist changes to disk, and update UI.
    
    @param model: Model that emitted signal
    @type model: L{BookmarkStore}
    @param path: Path of row that got deleted.
    @type path: tuple
    '''
    node = self._getElements()[path[0]]
    name = 'Bookmark%s' % str(path[0])
    bookmark = self._bookmarks_action_group.get_action(name)
    self._bookmarks_action_group.remove_action(bookmark)
    self._uimanager.remove_ui(bookmark.merge_id)
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
    if ''  in (bookmark.app, bookmark.path): return
    self.node.updateToPath(bookmark.app, map(int, bookmark.path.split(',')))

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
      if bookmark.get_property('label') == name:
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
      gtk.Dialog.__init__(self, _('Edit Bookmarks...'), 
                          buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
      self.set_default_size(480,240)
      self.connect('response', self._onResponse)
      hbox = gtk.HBox()
      hbox.set_spacing(3)
      tv = self._createTreeView(bookmarks_store)
      sw = gtk.ScrolledWindow()
      sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
      sw.set_shadow_type(gtk.SHADOW_IN)
      sw.add(tv)
      hbox.pack_start(sw)
      button_vbox = gtk.VBox()
      hbox.pack_start(button_vbox, False, False)
      add_button = gtk.Button('gtk-add')
      add_button.set_use_stock(True)
      add_button.connect('clicked', self._onAddClicked, tv)
      remove_button = gtk.Button('gtk-remove')
      remove_button.set_use_stock(True)
      remove_button.connect('clicked', self._onRemoveClicked, tv)
      jump_button = gtk.Button('gtk-jump-to')
      jump_button.set_use_stock(True)
      jump_button.connect('clicked', self._onJumpToClicked, tv)
      button_vbox.pack_start(add_button, False, False)
      button_vbox.pack_start(remove_button, False, False)
      button_vbox.pack_start(jump_button, False, False)
      self.vbox.add(hbox)
      hbox.set_border_width(3)
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
      if iter:
        model.remove(iter)

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
          int_path = map(int, new_text.split(','))
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
    def __init__(self, bookmark):
      '''
      Initialize the dialog.
      
      @param bookmark: New bookmark to edit.
      @type bookmark: L{BookmarkStore._Bookmark}
      '''
      gtk.Dialog.__init__(self, _('Add Bookmark...'))
      self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
      ok_button = self.add_button(gtk.STOCK_ADD, gtk.RESPONSE_OK)
      ok_button.set_sensitive(False)
      self.set_default_response(gtk.RESPONSE_OK)
      table = gtk.Table(3, 2, False)
      table.set_row_spacings(3)
      table.set_col_spacings(3)
      self.vbox.add(table)
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
        label_widget = gtk.Label(label)
        label_widget.set_alignment(0.0,0.5)
        label_acc = label_widget.get_accessible()
        entry_acc = entry.get_accessible()
        label_acc.add_relationship(atk.RELATION_LABEL_FOR, entry_acc)
        entry_acc.add_relationship(atk.RELATION_LABELLED_BY, label_acc)
        table.attach(gtk.Label(label), 0, 1, i, i+1, gtk.FILL, 0)
        table.attach(entry, 1, 2, i, i+1)
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

  class _Bookmark(gtk.Action):
    '''
    Bookmark object.

    @ivar title: Bookmark title (and label).
    @type title: string
    @ivar app: Application name.
    @type app: string
    @ivar path: Accessible path.
    @type path: string
    @ivar merge_id: Merge id of UIManager.
    @type merge_id: integer
    '''
    def __init__(self, name, title, app, path, merge_id):
      '''
      Initialize bookmark.
      
      @param name: Action name
      @type name: string
      @param title: Bookmark title (and label).
      @type title: string
      @param app: Application name.
      @type app: string
      @param path: Accessible path.
      @type path: string
      @param merge_id: Merge id of UIManager.
      @type merge_id: integer
      '''
      gtk.Action.__init__(self, name, title, None, None)
      self._title = title
      self._app = app
      self._path = path
      self.merge_id = merge_id

    def _getTitle(self):
      return self._title
    def _setTitle(self, title):
      self._title = title
      self.set_property('label', title)
    title = property(_getTitle, _setTitle)

    def _getApp(self):
      return self._app
    def _setApp(self, app):
      self._app = app
      self.notify('name')
    app = property(_getApp, _setApp)

    def _getPath(self):
      return self._path
    def _setPath(self, path):
      self._path = path
      self.notify('name')
    path = property(_getPath, _setPath)
