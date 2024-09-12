'''
Defines the manager for global hot keys.

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
from gi.repository.Gio import Settings as GSettings

from .i18n import _
import pyatspi

HOTKEYS_GSCHEMA = 'org.a11y.Accerciser.hotkeys'
HOTKEYS_BASEPATH = '/org/a11y/accerciser/hotkeys/'

COL_COMPONENT = 0
COL_DESC = 1
COL_CALLBACK = 2
COL_KEYPRESS = 3
COL_MOD = 4
COL_LOCALIZED_COMP = 5

def _charToKeySym(key):
  '''
  A convenience function to convert either a character, or key name to it's
  respective keyval

  @param key: The character or key name to convert.
  @type key: string

  @return: A key symbol
  @rtype: long
  '''
  try:
    rv = gdk.unicode_to_keyval(ord(key))
  except:
    rv = getattr(gdk, 'KEY_%s' % key)
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
    gtk.ListStore.__init__(self, str, str, object, int, int, str)
    self.connect('row-changed', self._onComboChanged)

    masks = [mask for mask in pyatspi.allModifiers()]
    pyatspi.Registry.registerKeystrokeListener(
      self._accEventKeyPressed, mask=masks, kind=(pyatspi.KEY_PRESSED_EVENT,))


  def _accEventKeyPressed(self, event):
    '''
    Handle certain key presses globally. Pass on to the hotkey manager the
    key combinations pressed for further processing.

    @param event: The event that is being handled.
    @type event: L{pyatspi.event.Event}
    '''
    handled = self.hotkeyPress(event.hw_code, event.modifiers)
    event.consume = handled


  def hotkeyPress(self, key, modifiers):
    '''
    Call the appropriate callbacks for given key combination. This method
    should be called by an at-spi keyboard:press event handler in the
    main program.

    @param key: The pressed key code.
    @type key: integer
    @param modifiers: The modifiers that were depressed during the keystroke.
    @type modifiers: integer
    '''
    km = gdk.Keymap.get_default()

    callback = None

    for combo in self:
      success, entries = km.get_entries_for_keyval(combo[COL_KEYPRESS])
      if not success: continue
      if key in [int(entry.keycode) for entry in entries] and \
            modifiers & combo[COL_MOD] == combo[COL_MOD]:
        callback = combo[COL_CALLBACK]
        if callback:
          callback()
    return bool(callback)

  def addKeyCombo(self, component, localized_component, description,
                  callback, keypress, modifiers):
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
    component_desc_pairs = list(zip([row[COL_COMPONENT] for row in self],
                               [row[COL_DESC] for row in self]))
    if (component, description) in component_desc_pairs:
      path = component_desc_pairs.index((component, description))
      self[path][COL_CALLBACK] = callback
    else:
      gspath = self._getComboGSettingsPath(component, description)
      gsettings = GSettings.new_with_path(HOTKEYS_GSCHEMA, gspath)
      if gsettings.get_string('hotkey-combo'):
        final_keypress, final_modifiers = gtk.accelerator_parse(
          gsettings.get_string('hotkey-combo'))
      else:
        final_keypress, final_modifiers = keypress, modifiers
      self.append([component, description, callback,
                   int(final_keypress), final_modifiers, localized_component])

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
    iter = self.get_iter_first()
    while iter:
      if self[iter][COL_CALLBACK] == callback:
        # We never really remove it, just set the callback to None
        self[iter][COL_CALLBACK] = ''
      iter = self.iter_next(iter)

  def _onComboChanged(self, model, path, iter):
    '''
    Callback for row changes. Copies the changed key combos over to gsettings.

    @param model: The model that emitted the signal. Should be this class instance.
    @type model: L{gtk.TreeModel}
    @param path: The path of the row that has changed.
    @type path: tuple
    @param iter: The iter of the row that has changed.
    @type iter: L{gtk.TreeIter}
    '''
    if not model[iter][COL_COMPONENT] or not model[iter][COL_DESC]:
      return

    gspath = self._getComboGSettingsPath(model[iter][COL_COMPONENT],
                                         model[iter][COL_DESC])
    gsettings = GSettings.new_with_path(HOTKEYS_GSCHEMA, gspath)
    combo_name = gtk.accelerator_name(model[iter][COL_KEYPRESS],
                                      gdk.ModifierType(model[iter][COL_MOD]))

    key = gsettings.get_string('hotkey-combo')

    if key != combo_name and key != '/':
      gsettings.set_string('hotkey-combo', combo_name)


  def _getComboGSettingsPath(self, component, description):
    '''
    Useful method that build and returns a gsettings path for a key combo.

    @param component: The component of the hotkey.
    @type component: string
    @param description: The description of the hotkey action
    @type description: string

    @return: A full gsettings path
    @rtype: string
    '''
    dash_component = self.__dasherize(component)
    dash_description = self.__dasherize(description)

    path = '/'.join([dash_component, dash_description])

    return HOTKEYS_BASEPATH + path + '/'


  def __dasherize(self, item):
    '''
    This method dasherize and decapitalize a given string.

    @param component: The given string
    @type component: string

    @return: A dasherized and decapitalized string
    @rtype: string
    '''
    return item.lower().replace(' ', '-')

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
    modelfilter = self.hotkey_manager.filter_new(None)
    modelfilter.set_visible_func(self._rowVisibleFunc, None)
    self.set_model(modelfilter)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Component'))
    tvc.pack_start(crt, True)
    tvc.add_attribute(crt, 'text', COL_COMPONENT)
    tvc.set_cell_data_func(crt, self._componentDataFunc, COL_COMPONENT)
    self.append_column(tvc)

    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Task'))
    tvc.pack_start(crt, True)
    tvc.add_attribute(crt, 'text', COL_DESC)
    tvc.set_cell_data_func(crt, self._translateDataFunc, COL_DESC)
    self.append_column(tvc)

    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Key'))
    tvc.set_min_width(64)
    tvc.pack_start(crt, True)
    crt.props.editable = True
    tvc.add_attribute(crt, 'text', COL_KEYPRESS)
    tvc.set_cell_data_func(crt, self._keyCellFunc)
    crt.connect('edited', self._onKeyChanged)
    self.append_column(tvc)

    crt = gtk.CellRendererToggle()
    tvc = gtk.TreeViewColumn(_('Alt'))
    tvc.pack_start(crt, True)
    tvc.set_cell_data_func(crt, self._modCellFunc, gdk.ModifierType.MOD1_MASK)
    crt.connect('toggled', self._onModToggled, gdk.ModifierType.MOD1_MASK)
    self.append_column(tvc)

    crt = gtk.CellRendererToggle()
    tvc = gtk.TreeViewColumn(_('Ctrl'))
    tvc.pack_start(crt, True)
    tvc.set_cell_data_func(crt, self._modCellFunc, \
                           gdk.ModifierType.CONTROL_MASK)
    crt.connect('toggled', self._onModToggled, gdk.ModifierType.CONTROL_MASK)
    self.append_column(tvc)

    crt = gtk.CellRendererToggle()
    tvc = gtk.TreeViewColumn(_('Shift'))
    tvc.pack_start(crt, True)
    tvc.set_cell_data_func(crt, self._modCellFunc, gdk.ModifierType.SHIFT_MASK)
    crt.connect('toggled', self._onModToggled, gdk.ModifierType.SHIFT_MASK)
    self.append_column(tvc)

  def _translateDataFunc(self, column, cell, model, iter, column_id):
    '''
    Show the component name as a translated string.

    @param column: The treeview column of the cell renderer.
    @type column: L{gtk.TreeViewColumn}
    @param cell: The cell rendere we need to modify.
    @type cell: L{gtk.CellRendererText}
    @param model: The treeview's model.
    @type model: L{gtk.ListStore}
    @param iter: The iter of the given cell data.
    @type iter: L{gtk.TreeIter}
    '''
    cell.set_property('text', _(model[iter][column_id]))

  def _componentDataFunc(self, column, cell, model, iter, column_id):
    '''
    Show the component name as a translated string.

    @param column: The treeview column of the cell renderer.
    @type column: L{gtk.TreeViewColumn}
    @param cell: The cell rendere we need to modify.
    @type cell: L{gtk.CellRendererText}
    @param model: The treeview's model.
    @type model: L{gtk.ListStore}
    @param iter: The iter of the given cell data.
    @type iter: L{gtk.TreeIter}
    '''
    cell.set_property('text', model[iter][COL_LOCALIZED_COMP] or \
                        model[iter][COL_COMPONENT])

  def _keyCellFunc(self, column, cell, model, iter, foo=None):
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
                        gdk.keyval_name(model[iter][COL_KEYPRESS]))
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
    self.hotkey_manager[path][COL_KEYPRESS] = int(keysym)

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

  def _rowVisibleFunc(self, model, iter, foo=None):
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
