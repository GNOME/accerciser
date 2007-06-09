import gtk, atk, os
from xml.dom.minidom import getDOMImplementation, parse, Element
from i18n import _
from pyatspi import getPath

COL_NAME = 0
COL_APP = 1
COL_PATH = 2
COL_MENUITEM = 3
TYPE_COLS = ['name', 'app', 'path']

BOOKMARKS_PATH = os.path.join(os.environ['HOME'], '.accerciser')
BOOKMARKS_FILE = 'bookmarks.xml'

class BookmarkStore(gtk.ListStore):
  def __init__(self, bookmarks_menu, node):
    gtk.ListStore.__init__(self, str, str, str, object)
    self._menu = bookmarks_menu
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
    
  def _cleanDoc(self):
    elements = self._getElements()
    for node in self._xmldoc.documentElement.childNodes:
      if node not in elements:
        self._xmldoc.documentElement.removeChild(node)

  def _populateModel(self):
    for node in self._getElements():
      row = []
      for i, key in enumerate(TYPE_COLS):
        row.append(node.getAttribute(key))
      menu_item = self._newMenuItem(row[COL_NAME])
      row.append(menu_item)
      self.append(row)

  def _newMenuItem(self, acc_name):
    menu_item = gtk.MenuItem(acc_name, False)
    menu_item.connect('activate', self._onBookmarkActivate)
    self._menu.append(menu_item)
    menu_item.show_all()
    return menu_item

  def _getElements(self):
    return filter(lambda x: isinstance(x, Element),
                  self._xmldoc.documentElement.childNodes)

  def _onRowChanged(self, model, path, iter):
    if model[iter][COL_NAME] and model[iter][COL_MENUITEM]:
      menu_item = model[iter][COL_MENUITEM]
      item_label = menu_item.child
      if item_label.get_text() != model[iter][COL_NAME]:
        item_label.set_text(model[iter][COL_NAME])
    node = self._getElements()[path[0]]
    for i, key in enumerate(TYPE_COLS):
      if model[iter][i] is not None:
        node.setAttribute(key, model[iter][i])
    self._persist()

  def remove(self, iter):
    menu_item = self[iter][COL_MENUITEM]
    menu_item.destroy()
    gtk.ListStore.remove(self, iter)

  def _onRowDeleted(self, model, path):
    node = self._getElements()[path[0]]
    self._xmldoc.documentElement.removeChild(node)
    self._persist()

  def _onRowInserted(self, model, path, iter):
    node = self._xmldoc.createElement('bookmark')
    self._xmldoc.documentElement.appendChild(node)
    self._persist()

  def _persist(self):
    bookmarks_fn = os.path.join(BOOKMARKS_PATH, BOOKMARKS_FILE)
    try:
      if not os.path.exists(os.path.dirname(bookmarks_fn)):
        os.mkdir(os.path.dirname(bookmarks_fn))
      f = open(bookmarks_fn, 'w')
    except:
      return
    self._xmldoc.writexml(f, '', '  ', '\n')
    f.close()

  def _onBookmarkActivate(self, menu_item):
    for row in self:
      if row[COL_MENUITEM] == menu_item:
        self.jumpTo(row.iter)

  def jumpTo(self, iter):
    if not self[iter][COL_APP]: return
    if self[iter][COL_PATH]:
      path = map(int, self[iter][COL_PATH].split(','))
    else:
      path = []
    self.node.updateToPath(self[iter][COL_APP], path)

  def addBookmark(self):
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
    menu_item = self._newMenuItem(bm_name)
    return self.append([bm_name, app.name, path, menu_item])
  
  def _nameIsTaken(self, name):
    for row in self:
      if row[COL_NAME] == name:
        return True
    return False

  def EditDialog(self):
    return self._EditDialog(self)

  def NewBookmarkDialog(self, parent, iter):
    return self._NewBookmarkDialog(parent, self, iter)

  class _EditDialog(gtk.Dialog):
    def __init__(self, bookmarks_store):
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
      add_button.connect('clicked', self._onAddClicked, bookmarks_store)
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

    def _onAddClicked(self, button, model):
      iter = model.addBookmark(_('New bookmark'), '', '')
      path = model.get_path(iter)

    def _onRemoveClicked(self, button, tv):
      selection = tv.get_selection()
      model, iter = selection.get_selected()
      if iter:
        model.remove(iter)

    def _onJumpToClicked(self, button, tv):
      selection = tv.get_selection()
      model, iter = selection.get_selected()
      model.jumpTo(iter)

    def _onResponse(self, dialog, response):
      self.destroy()

    def _createTreeView(self, model):
      tv = gtk.TreeView()
      tv.set_model(model)

      crt = gtk.CellRendererText()
      crt.set_property('editable', True)
      crt.connect('edited', self._onCellEdited, model, COL_NAME)
      tvc = gtk.TreeViewColumn(_('Title'))
      tvc.pack_start(crt, True)
      tvc.set_attributes(crt, text=COL_NAME)
      tv.append_column(tvc)

      crt = gtk.CellRendererText()
      crt.set_property('editable', True)
      crt.connect('edited', self._onCellEdited, model, COL_APP)
      tvc = gtk.TreeViewColumn(_('Application'))
      tvc.pack_start(crt, True)
      tvc.set_attributes(crt, text=COL_APP)
      tv.append_column(tvc)

      crt = gtk.CellRendererText()
      crt.set_property('editable', True)
      crt.connect('edited', self._onCellEdited, model, COL_PATH)
      tvc = gtk.TreeViewColumn(_('Path'))
      tvc.pack_start(crt, True)
      tvc.set_attributes(crt, text=COL_PATH)
      tv.append_column(tvc)

      return tv

    def _onCellEdited(self, cellrenderer, path, new_text, model, col_id):
      if col_id == COL_NAME and new_text == '':
        return
      if col_id == COL_PATH:
        try:
          int_path = map(int, new_text.split(','))
        except ValueError:
          return
      model[path][col_id] = new_text

  class _NewBookmarkDialog(gtk.Dialog):
    def __init__(self, parent, model, iter):
      gtk.Dialog.__init__(self, _('Add Bookmark...'), 
                          parent, gtk.DIALOG_MODAL)
      row_reference = gtk.TreeRowReference(model, model.get_path(iter))
      self.connect('response', self._onResponse, row_reference)
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
                                             model[iter][COL_NAME],
                                            self._title_entry),
                                           (_('Application:'), 
                                            model[iter][COL_APP],
                                            self._app_entry),
                                           (_('Path:'), 
                                            model[iter][COL_PATH],
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
      text = entry.get_text()
      not_empty = bool(text)
      button.set_sensitive(not_empty)

    def _onEnter(self, entry, button):
      button.clicked()

    def _onResponse(self, dialog, response_id, row_reference):
      model = row_reference.get_model()
      path = row_reference.get_path()
      if response_id == gtk.RESPONSE_OK and row_reference.valid():
        model[path][COL_NAME] = self._title_entry.get_text()
        model[path][COL_APP] = self._app_entry.get_text()
        model[path][COL_PATH] = self._path_entry.get_text()
      else:
        iter = model.get_iter(path)
        model.remove(iter)
      self.destroy()
