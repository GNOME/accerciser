import gtk, gconf
from pyLinAcc import Constants

GCONF_HOTKEYS = '/apps/accerciser/global_hotkeys'

COL_COMPONENT = 0
COL_DESC = 1
COL_CALLBACK = 2
COL_KEYPRESS = 3
COL_MOD = 4

def _charToKeySym(key):
  '''
  A convinience function to convert either a character, or key name to it's
  respective keyval

  @param key: The character or key name to convert.
  @type key: string
  
  @return: A key symbol
  @rtype: long
  '''
  try:
    rv = gtk.gdk.unicode_to_keyval(ord(key))
  except:
    rv = getattr(gtk.keysyms, key)
  return rv


class HotkeyManager(gtk.ListStore):
  '''
  A model that stores all of the global key bindings. All accerciser components
  that need global hotkeys should register the key combination and callback
  with the main instance of this class.
  '''
  def __init__(self):
    '''
    Constructor for the L{HotkeyManager}
    '''
    gtk.ListStore.__init__(self, str, str, object, int, int)
    self.connect('row-changed', self._onComboChanged)
    self.gconf_client = gconf.client_get_default()
    
  def hotkeyPress(self, key, modifiers):
    '''
    Call the appropriate callbacks for given key combination. This method 
    should be called by an at-spi keyboard:press event handler in the 
    main program. 

    @param key: The pressed key name or symbol.
    @type key: string
    @param modifiers: The modifiers that were depressed during the keystroke.
    @type modifiers: integer
    '''
    for combo in self:
      if _charToKeySym(key) == combo[COL_KEYPRESS] and \
            modifiers & combo[COL_MOD] == combo[COL_MOD]:
        callback = combo[COL_CALLBACK]
        if callback:
          callback()
  
  def addKeyCombo(self, component, description, callback, keypress, modifiers):
    '''
    Adds the given key combination with the appropriate callbacks to 
    the L{HotkeyManager}. If an identical description with the identical 
    component already exists in the model, just reassign with the new callback.

    I{Note:} It is important that the component and description strings be
    unique.

    @param component: The component name, usually the plugin name, or "Core".
    @type component: string
    @param description: A description of the action performed during the given
    keycombo.
    @type description: string
    @param callback: The callback to call when the given key combination 
    is pressed.
    @type callback: callable
    @param keypress: The key symbol of the keystroke that performs given operation.
    @type keypress: long
    @param modifiers: The modifiers that must be depressed for function to 
    be perfomed.
    @type modifiers: int
    '''
    component_desc_pairs = zip([row[COL_COMPONENT] for row in self],
                               [row[COL_DESC] for row in self])
    if (component, description) in component_desc_pairs:
      path = component_desc_pairs.index((component, description))
      self[path][COL_CALLBACK] = callback
    else:
      combo_gconf_key = self._getComboGConfKey(component, description)
      if self.gconf_client.get(combo_gconf_key):
        final_keypress, final_modifiers = \
            self._keyComboParse(self.gconf_client.get_string(combo_gconf_key))
      else:
        final_keypress, final_modifiers = keypress, modifiers
      self.append([component, description, callback, final_keypress, final_modifiers])

  def removeKeyCombo(self, component, description, callback, key, modifiers):
    '''
    Removes the given callback from L{HotkeyManager}. It does not erase the
    entire key combo entry.

    @param component: The component name, usually the plugin name, or "Core".
    @type component: string
    @param description: A description of the action performed during the given
    keycombo.
    @type description: string
    @param callback: The callback to call when the given key combination 
    is pressed.
    @type callback: callable
    @param key: The key symbol of the keystroke that performs given operation.
    @type key: long
    @param modifiers: The modifiers that must be depressed for function to 
    be perfomed.
    @type modifiers: int
    '''
    iter = self.get_iter_root()
    while iter:
      if self[iter][COL_CALLBACK] == callback:
        # We never really remove it, just set the callback to None
        self[iter][COL_CALLBACK] = None
      iter = self.iter_next(iter)
    
  def _onComboChanged(self, model, path, iter):
    '''
    Callback for row changes. Copies the changed key combos over to gconf.

    @param model: The model that emitted the signal. Should be this class instance.
    @type model: L{gtk.TreeModel}
    @param path: The path of the row that has changed.
    @type path: tuple
    @param iter: The iter of the row that has changed.
    @type iter: L{gtk.TreeIter}
    '''
    if not model[iter][COL_COMPONENT] or not model[iter][COL_DESC]:
      return
    combo_gconf_key = self._getComboGConfKey(model[iter][COL_COMPONENT], 
                                             model[iter][COL_DESC])
    combo_name = self._keyComboName(model[iter][COL_KEYPRESS], model[iter][COL_MOD])
    if self.gconf_client.get_string(combo_gconf_key) != combo_name:
      self.gconf_client.set_string(combo_gconf_key, combo_name)
  
  def _getComboGConfKey(self, component, description):
    '''
    A convinience method to expand the full gconf path for a specific key combo.

    @param component: The component of the hotkey.
    @type component: string
    @param description: The description of the hotkey action
    @type description: string
    
    @return: A full gconf key name
    @rtype: string
    '''
    combo_gconf_key = '%s/%s/%s/key_combo' % \
        (GCONF_HOTKEYS, gconf.escape_key(component, len(component)),
         gconf.escape_key(description, len(description)))
    return combo_gconf_key

  def _keyComboParse(self, combo_string):
    '''
    Gets the key symbol and the modifier mask from a human readable string.
    This convinience method is important because gtk.accelerator_parse ignores the
    case of the keys.

    @param combo_string: The key combo string, for example, '<Alt>g'.
    @type combo_string: string

    @return: The key symbol and modifiers mask.
    @rtype: tuple
    '''
    if not combo_string:
      return (-1, 0)
    key, modifiers = gtk.accelerator_parse(combo_string)
    key = gtk.gdk.keyval_from_name(combo_string.split('>')[-1]) or -1
    return key, modifiers

  def _keyComboName(self, key, modifiers):
    '''
    Gets a human readable string from a key symbol and the modifier mask.
    This convinience method is important because gtk.accelerator_name ignores the
    case of the keys.

    @param key: A key symbol.
    @type key: int
    @param modifiers: Modifiers mask
    @type modifiers: int

    @return: The key combo string, for example, '<Alt>g'.
    @rtype: string
    '''
    combo_string = gtk.accelerator_name(0, modifiers)
    combo_string += gtk.gdk.keyval_name(key) or ''
    return combo_string

class HotkeyTreeView(gtk.TreeView):
  '''
  A tree view of the variuos global hotkey combinations. The keys and 
  modifiers could also be changed through this widget.
  '''
  def __init__(self, hotkey_manager):
    '''
    Construct the tree view with the given L{HotkeyManager}.
    
    @ivar hotkey_manager: The manager we wish to view.
    @type hotkey_manager: L{HotkeyManager}

    @param hotkey_manager: The manager we wish to view.
    @type hotkey_manager: L{HotkeyManager}
    '''
    gtk.TreeView.__init__(self)
    self.hotkey_manager = hotkey_manager
    modelfilter = self.hotkey_manager.filter_new()
    modelfilter.set_visible_func(self._rowVisibleFunc)
    self.set_model(modelfilter)
    crt = gtk.CellRendererText()
    #crc.connect('toggled', self._onPluginToggled)
    tvc = gtk.TreeViewColumn('Component')
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=COL_COMPONENT)
    self.append_column(tvc)
    
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn('Task')
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=COL_DESC)
    self.append_column(tvc)

    crt = gtk.CellRendererCombo()
    tvc = gtk.TreeViewColumn('Key')
    tvc.set_min_width(64)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=COL_KEYPRESS)
    tvc.set_cell_data_func(crt, self._keyCellFunc)
    crt.set_property('editable', True)
    crt.set_property('model', self._buildKeySymsModel())
    crt.set_property('text-column', 1)
    crt.set_property('has-entry', True)
    crt.connect('edited', self._onKeyChanged)
    self.append_column(tvc)

    crt = gtk.CellRendererToggle()
    tvc = gtk.TreeViewColumn('Alt')
    tvc.pack_start(crt, True)
    tvc.set_cell_data_func(crt, self._modCellFunc, gtk.gdk.MOD1_MASK)
    crt.connect('toggled', self._onModToggled, gtk.gdk.MOD1_MASK)
    self.append_column(tvc)

    crt = gtk.CellRendererToggle()
    tvc = gtk.TreeViewColumn('Ctrl')
    tvc.pack_start(crt, True)
    tvc.set_cell_data_func(crt, self._modCellFunc, gtk.gdk.CONTROL_MASK)
    crt.connect('toggled', self._onModToggled, gtk.gdk.CONTROL_MASK)
    self.append_column(tvc)

    crt = gtk.CellRendererToggle()
    tvc = gtk.TreeViewColumn('Shift')
    tvc.pack_start(crt, True)
    tvc.set_cell_data_func(crt, self._modCellFunc, gtk.gdk.SHIFT_MASK)
    crt.connect('toggled', self._onModToggled, gtk.gdk.SHIFT_MASK)
    self.append_column(tvc)
  
  def _buildKeySymsModel(self):
    '''
    Build a model that represents all the possible keys that could be 
    configured as hotkeys.
    '''
    model = gtk.TreeStore(long, str)
    iter = model.append(None, [-1, 'Alphanumeric'])
    for keyval in range(48, 58)+range(65, 91)+range(97, 123):
      model.append(iter, [keyval, gtk.gdk.keyval_name(keyval)])
    iter = model.append(None, [-1, 'Keypad'])
    for keyval in range(65408, 65470):
      if not gtk.gdk.keyval_name(keyval) or \
            not gtk.gdk.keyval_name(keyval).startswith('KP'):
        continue
      model.append(iter, [keyval, gtk.gdk.keyval_name(keyval)])
    iter = model.append(None, [-1, 'Functions'])
    for keyval in range(65470, 65505):
      if not gtk.gdk.keyval_name(keyval): continue
      model.append(iter, [keyval, gtk.gdk.keyval_name(keyval)])
    iter = model.append(None, [-1, 'Extras'])
    for keyval in range(32, 48)+range(58,64)+range(91,97)+range(123,192):
      if not gtk.gdk.keyval_name(keyval): continue
      model.append(iter, [keyval, gtk.gdk.keyval_name(keyval)])
    return model

  def _keyCellFunc(self, column, cell, model, iter):
    '''
    Show the key symbol as a string for easy readability.

    @param column: The treeview column of the cell renderer.
    @type column: L{gtk.TreeViewColumn}
    @param column: The cell rendere we need to modify.
    @type column: L{gtk.CellRendererText}
    @param model: The treeview's model.
    @type model: L{gtk.ListStore}
    @param iter: The iter of the given cell data.
    @type iter: L{gtk.TreeIter}
    '''
    if model[iter][COL_KEYPRESS] > 0:
      cell.set_property('text', 
                        gtk.gdk.keyval_name(model[iter][COL_KEYPRESS]))
      cell.set_property('sensitive', True)
    else:
      cell.set_property('text', '<select key>')
      cell.set_property('sensitive', False)

  def _modCellFunc(self, column, cell, model, iter, mask):
    '''
    Show the given modifier mask as toggled or not.

    @param column: The treeview column of the cell renderer.
    @type column: L{gtk.TreeViewColumn}
    @param column: The cell rendere we need to modify.
    @type column: L{gtk.CellRendererText}
    @param model: The treeview's model.
    @type model: L{gtk.ListStore}
    @param iter: The iter of the given cell data.
    @type iter: L{gtk.TreeIter}
    @param mask: A modifier mask.
    @type mask: integer
    '''
    cell.set_property('active', bool(mask & model[iter][COL_MOD]))

  def _onKeyChanged(self, cellrenderertext, path, new_text):
    '''
    A callback for the key cellrenderer when 'edited'. Model must be 
    changed accordingly.

    @param cellrenderertext: The cell renderer that emitted the signal
    @type cellrenderertext: L{gtk.CellRendererText}
    @param path: Path of the edited cellrenderer.
    @type path: tuple
    @param new_text: The new text that was entered.
    @type new_text: string
    '''
    keysym = -1
    if new_text:
      try:
        keysym = _charToKeySym(new_text)
      except:
        keysym = _charToKeySym(new_text[0])
    self.hotkey_manager[path][COL_KEYPRESS] = keysym
  
  def _onModToggled(self, renderer_toggle, path, mask):
    '''
    A callback for the modifiers' cellrenderers when 'toggled'. 
    Model must be changed accordingly.

    @param renderer_toggle: The cell renderer that emitted the signal
    @type renderer_toggle: L{gtk.CellRendererToggle}
    @param path: Path of the edited cellrenderer.
    @type path: tuple
    @param mask: Modifier mask that must be inverted.
    @type new_text: integer
    '''
    self.hotkey_manager[path][COL_MOD] ^= mask

  def _rowVisibleFunc(self, model, iter):
    '''
    A filter function to hide the rows that do not contain valid callbacks.
    This is usually the case when a plugin is disabled.

    @param model: The view's model.
    @type model: L{gtk.ListStore}
    @param iter: The iter of the row in question.
    @type iter: L{gtk.TreeIter}

    @return: True if row should be displayed.
    @rtype: boolean
    '''
    return bool(model[iter][COL_CALLBACK])
