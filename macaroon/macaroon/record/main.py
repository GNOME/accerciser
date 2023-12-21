# Macaroon - a desktop macro tool
# Copyright (C) 2007 Eitan Isaacson <eitan@ascender.com>
# All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "COPYING" in the source distribution for more information.

# Headers in this file shall remain intact.

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import GtkSource

from . import script_factory
from queue import Queue
from macaroon.playback import MacroSequence

APP_ID = None

MacroSequence.startReally = MacroSequence.start
MacroSequence.start = lambda x: None

from .about import MacaroonAboutDialog

import pyatspi

_ = lambda x: x


class Main:
  start_tooltip = _('Record new keyboard macro')
  stop_tooltip = _('Stop recording macro')
  def __init__(self):
    status_icon = Gtk.StatusIcon.new_from_stock(Gtk.STOCK_MEDIA_RECORD)
    status_icon.connect('activate', self._onActivate)
    status_icon.connect('popup-menu', self._onPopup)
    status_icon.set_tooltip_text(self.start_tooltip)
    self.ui_manager = self._newUIManager()
    self.script_buffer = ScriptBuffer(self.ui_manager)
    self.script_buffer.clearBuffer()
    self.script_buffer.connect('notify::recording',
                               self._onRecordChange, status_icon)
    self.macro_preview = None
    # Get program ID
    global APP_ID
#    from gnome import program_get
#    _prog = program_get()
#    if _prog is not None:
#      APP_ID = _prog.get_app_id()

    pyatspi.Registry.start()

  def _onRecordChange(self, gobject, pspec, status_icon):
    is_recording = self.script_buffer.get_property('recording')
    if is_recording:
      status_icon.set_from_stock(Gtk.STOCK_MEDIA_STOP)
      status_icon.set_tooltip_text(self.stop_tooltip)
    else:
      status_icon.set_from_stock(Gtk.STOCK_MEDIA_RECORD)
      status_icon.set_tooltip_text(self.start_tooltip)

  def _onActivate(self, status_icon):
    is_recording = self.script_buffer.get_property('recording')
    if not is_recording:
      self.script_buffer.startRecord()
    else:
      self.script_buffer.stopRecord()
      if self.macro_preview is None:
        self.macro_preview = MacroPreview(self.script_buffer)
      self.macro_preview.show_all()

  def _newUIManager(self):
    popup_ui = '''
<ui>
<popup>
    <placeholder name="ScriptType">
    </placeholder>
    <separator />
    <menuitem action="About" />
    <separator />
    <menuitem action="Quit" />
</popup>
</ui>'''
    main_action_group = Gtk.ActionGroup('MenuActions')
    main_action_group.add_actions([
        ('ScriptType', None, 'Script type'),
        ('Quit', Gtk.STOCK_QUIT, _('_Quit'), None, None, self._onQuit),
        ('About', Gtk.STOCK_ABOUT, _('_About'), None, None, self._onAbout)])
    ui_manager = Gtk.UIManager()
    ui_manager.add_ui_from_string(popup_ui)
    ui_manager.insert_action_group(main_action_group, 0)
    return ui_manager

  def _onPopup(self, status_icon, button, activate_time):
    menu = self.ui_manager.get_widget('/popup')
    menu.popup(None, None, Gtk.StatusIcon.position_menu,
               status_icon, button, activate_time)

  def _onQuit(self, action):
    pyatspi.Registry.stop()

  def _onAbout(self, action):
    '''
    Shows the about dialog.

    @param widget: The widget that emitted the signal that callback caught.
    @type widget: L{Gtk.Widget}
    '''
    about = MacaroonAboutDialog()
    about.show_all()


class MacroPreview(Gtk.Window):
  def __init__(self, script_buffer):
    GObject.GObject.__init__(self)
    self.set_title(_('Macro preview'))
    self.set_default_size(480, 720)
    self.set_border_width(6)
    self.connect('delete-event', self._onDelete)
    self.script_buffer = script_buffer
    text_view = GtkSource.View.new_with_buffer(self.script_buffer)
    text_view.set_editable(True)
    text_view.set_cursor_visible(True)
    text_view.modify_font(Pango.FontDescription('Mono'))
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    sw.set_shadow_type(Gtk.ShadowType.IN)
    sw.add(text_view)
    vbox = Gtk.VBox()
    vbox.set_spacing(3)
    vbox.pack_start(sw, True, True, 0)
    bbox = Gtk.HButtonBox()
    bbox.set_layout(Gtk.ButtonBoxStyle.START)
    for label, callback in [(Gtk.STOCK_SAVE_AS, self._onSave),
                            (Gtk.STOCK_CLEAR, self._onClear),
                            (Gtk.STOCK_MEDIA_RECORD, self._onRecord),
                            (Gtk.STOCK_MEDIA_PLAY, self._onPlay)]:
      button = Gtk.Button(label)
      button.set_use_stock(True)
      button.connect('clicked', callback)
      bbox.pack_start(button, True, True, 0)
      if label == Gtk.STOCK_MEDIA_RECORD:
        self.script_buffer.connect('notify::recording',
                                   self._onRecordChange, button)
    vbox.pack_start(bbox, False, False, 0)
    self.progress_bar = Gtk.ProgressBar()
    vbox.pack_start(self.progress_bar, False, False, 0)
    self.add(vbox)

  def _onPlay(self, button):
    script = self.script_buffer.get_text(self.script_buffer.get_start_iter(),
                                         self.script_buffer.get_end_iter(),
                                         True)
    script_scope = {}
    exec(script, script_scope)
    sequence = script_scope.get('sequence')
    sequence.connect('step-done', self._onSeqStepDone, button)
    if sequence and len(sequence.steps) > 0:
      button.set_sensitive(False)
      first_action = sequence.steps[0]
      self.progress_bar.set_fraction(0.0)
      self.progress_bar.set_text(str(first_action))
      sequence.startReally(False)

  def _onSeqStepDone(self, sequence, step, button):
    fraction = float(step + 1)/len(sequence.steps)
    self.progress_bar.set_fraction(fraction)
    if fraction >= 1.0:
      button.set_sensitive(True)
      self.progress_bar.set_text(_('Done'))
    else:
      action = sequence.steps[step + 1]
      self.progress_bar.set_text(str(action))

  def _onRecordChange(self, gobject, pspec, button):
    is_recording = self.script_buffer.get_property('recording')
    if is_recording:
      button.set_label(Gtk.STOCK_MEDIA_STOP)
    else:
      button.set_label(Gtk.STOCK_MEDIA_RECORD)

  def _onDelete(self, window, event):
    if self._askLoseChanges():
      self.script_buffer.clearBuffer()
      self.hide()
    return True

  def _onSave(self, button):
    '''
    Callback for 'save' button. Raises file chooser dialog for saving
    contents of script buffer.

    @param button: Button that was clicked.
    @type button: Gtk.Button
    '''
    save_dialog = Gtk.FileChooserDialog(
      'Save recorded script',
      action=Gtk.FileChooserAction.SAVE,
      buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
               Gtk.STOCK_OK, Gtk.ResponseType.OK))
    save_dialog.set_do_overwrite_confirmation(True)
    save_dialog.set_default_response(Gtk.ResponseType.OK)
    save_dialog.show_all()
    response = save_dialog.run()
    if response == Gtk.ResponseType.OK:
      save_to = open(save_dialog.get_filename(), 'w')
      save_to.write(self.script_buffer.get_text(
          self.script_buffer.get_start_iter(),
          self.script_buffer.get_end_iter(), True))
      save_to.close()
      self.script_buffer.set_modified(False)
    save_dialog.destroy()

  def _onClear(self, button):
    '''
    Callback for 'clear' button press.

    @param button: Button that was clicked.
    @type button: Gtk.Button
    '''
    if self._askLoseChanges():
      self.script_buffer.clearBuffer()

  def _onRecord(self, button):
    is_recording = self.script_buffer.get_property('recording')
    if not is_recording:
      self.script_buffer.startRecord()
    else:
      self.script_buffer.stopRecord()

  def _askLoseChanges(self):
    '''
    Raises a dialog that asks the user to confirm the loss of the current
    script in the buffer.

    @return: True if user confirms.
    @rtype: boolean
    '''
    if not self.script_buffer.get_modified():
      return True
    dialog = Gtk.MessageDialog(self.get_toplevel(), 0, Gtk.MessageType.WARNING,
                               Gtk.ButtonsType.OK_CANCEL,
                               _('The current script will be lost.'))
    dialog.set_title(_('Confirm clear'))
    response_id = dialog.run()
    dialog.destroy()
    if response_id == Gtk.ResponseType.OK:
      return True
    else:
      return False

class ScriptBuffer(GtkSource.Buffer):
  __gproperties__ = {
    'recording': (GObject.TYPE_BOOLEAN,
                  'Is recording',
                  'True if script buffer is recording',
                  False, GObject.PARAM_READWRITE)}
  factory_mapping = {'Level1' : script_factory.Level1SequenceFactory,
                     'Level2' : script_factory.Level2SequenceFactory}
  def __init__(self, uimanager):
    GtkSource.Buffer.__init__(self)
    lm = GtkSource.LanguageManager()
    lang = lm.guess_language(None, 'text/x-python')
    self.set_language(lang)
    self.set_highlight_syntax(True)
    self.script_factory = self.factory_mapping['Level2'](True)
    self._recording = False
    self._uimanager = uimanager
    self._addToUIManager()

  def _addToUIManager(self):
    self.script_type_actions = Gtk.ActionGroup('ScriptTypes')
    self.script_type_actions.add_radio_actions(
        (('Level1', None, 'Level 1', None, None, 1),
         ('Level2', None, 'Level 2', None, None, 2)),
        2, self._onChange)
    self._wait_for_focus_toggle = Gtk.ToggleAction('WaitForFocus',
                                                   'Record focus events',
                                                   None, None)
    self._wait_for_focus_toggle.set_active(True)
    self._wait_for_focus_toggle.connect('toggled', self._onWaitForFocusToggled)
    self.script_type_actions.add_action(self._wait_for_focus_toggle)
    script_type_ui = '''
<ui>
<popup>
    <placeholder name="ScriptType">
      <menuitem action="Level1" />
      <menuitem action="Level2" />
      <separator />
      <menuitem action="WaitForFocus" />
     </placeholder>
</popup>
</ui>'''
    self._uimanager.add_ui_from_string(script_type_ui)
    self._uimanager.insert_action_group(self.script_type_actions, 0)

  def startRecord(self):
    pyatspi.Registry.registerEventListener(self._onWindowActivate,
                                           'window:activate')
    pyatspi.Registry.registerEventListener(self._onFocus,
                                           'focus')
    pyatspi.Registry.registerEventListener(self._onDocLoad,
                                           'document:load-complete')
    pyatspi.Registry.registerKeystrokeListener(
      self._onKeystroke,
      mask = list(range(256)),
      kind=(pyatspi.KEY_PRESSED_EVENT, pyatspi.KEY_RELEASED_EVENT))
    self.set_property('recording', True)

  def stopRecord(self):
    pyatspi.Registry.deregisterEventListener(self._onWindowActivate,
                                             'window:activate')
    pyatspi.Registry.deregisterEventListener(self._onFocus,
                                             'focus')
    pyatspi.Registry.deregisterEventListener(self._onDocLoad,
                                             'document:load-complete')
    pyatspi.Registry.deregisterKeystrokeListener(
      self._onKeystroke,
      mask = list(range(256)),
      kind=(pyatspi.KEY_PRESSED_EVENT, pyatspi.KEY_RELEASED_EVENT))
    self.script_factory.terminateScript()
    while self.script_factory.commands_queue.qsize():
      self._appendText(self.script_factory.commands_queue.get_nowait())
    self.set_property('recording', False)

  def clearBuffer(self):
    '''
    Clears the script text buffer and inserts the intepreter and import line.
    '''
    self.set_text('%s\n\n%s\n\n' % \
                    (self.script_factory.intepreter_line,
                     self.script_factory.import_line))
    self.set_modified(False)

  def _onWindowActivate(self, event):
    '''
    Callback for window focus events. Calls the script factory and flushes
    it's queue.

    @param event: Focus at-spi event.
    @type event: Accessibility.Event
    '''
    if self._isMyApp(event.source):
      return
    self.script_factory.windowActivateCommand(event)

  def _onFocus(self, event):
    '''
    Callback for focus events. Calls the script factory and flushes
    it's queue.

    @param event: Focus at-spi event.
    @type event: Accessibility.Event
    '''
    if self._isMyApp(event.source):
      return
    app = event.source.getApplication()
    triggering_hotkey = None
    if getattr(app, 'name', None) == 'gnome-panel':
      if event.source.getRole() == pyatspi.ROLE_MENU and \
            event.source.parent.getRole() == pyatspi.ROLE_MENU_BAR:
        # A wild assumption that this was triggered with <Alt>F1
        triggering_hotkey = '<Alt>F1'
      if event.source.getRole() == pyatspi.ROLE_COMBO_BOX:
        triggering_hotkey = '<Alt>F2'
    elif getattr(app, 'name', None) == 'gnome-screenshot' and \
          event.source.getRole() == pyatspi.ROLE_TEXT and \
          pyatspi.getPath(event.source) == [0, 0, 0, 0, 1, 1]:
      triggering_hotkey = 'Print'

    if triggering_hotkey is not None:
      fake_event = _FakeDeviceEvent(triggering_hotkey, pyatspi.KEY_PRESSED_EVENT)
      self._onKeystroke(fake_event)

    self.script_factory.focusCommand(event)

    if triggering_hotkey is not None:
      fake_event = _FakeDeviceEvent(triggering_hotkey, pyatspi.KEY_RELEASED_EVENT)
      self._onKeystroke(fake_event)

    while self.script_factory.commands_queue.qsize():
      self._appendText(self.script_factory.commands_queue.get_nowait())

  def _onKeystroke(self, event):
    '''
    Callback for key press events. Calls the script factory and flushes
    it's queue.

    @param event: Key press at-spi event.
    @type event: Accessibility.DeviceEvent
    '''
    if event.type == pyatspi.KEY_PRESSED_EVENT:
      self.script_factory.keyPressCommand(event)
    elif event.type == pyatspi.KEY_RELEASED_EVENT:
      self.script_factory.keyReleaseCommand(event)
    while self.script_factory.commands_queue.qsize():
      self._appendText(self.script_factory.commands_queue.get_nowait())

  def _onDocLoad(self, event):
    self.script_factory.docLoadCommand()
    while self.script_factory.commands_queue.qsize():
      self._appendText(self.script_factory.commands_queue.get_nowait())

  def _isMyApp(self, acc):
    global APP_ID
    if APP_ID is not None:
      app = acc.getApplication()
      return getattr(app, 'name', None) == APP_ID
    else:
      return False

  def _appendText(self, text):
    self.insert(self.get_end_iter(), text)

  def do_set_property(self, pspec, value):
    if pspec.name == 'recording':
      self._recording = value

  def do_get_property(self, pspec):
    if pspec.name == 'recording':
      return self._recording

  def _onChange(self, action, current):
    factory = self.factory_mapping.get(current.get_name(),
                                       script_factory.Level1SequenceFactory)
    self.script_factory = factory(self._wait_for_focus_toggle.get_active())

  def _onWaitForFocusToggled(self, action):
    factory = self.script_factory.__class__
    self.script_factory = factory(self._wait_for_focus_toggle.get_active())

class _FakeDeviceEvent(object):
  def __init__(self, key_combo, type):
    id = Gdk.keyval_from_name(key_combo)
    if Gdk.keyval_from_name(key_combo):
      modifiers = 0
    else:
      id, modifiers = Gtk.accelerator_parse(key_combo)
    keymap = Gdk.Keymap.get_default()
    success, map_entry = keymap.get_entries_for_keyval(65471)
    self.type = type
    self.id = id
    self.hw_code = map_entry[0].keycode
    self.modifiers = int(modifiers)
    self.timestamp = 0
    self.event_string = Gdk.keyval_name(id)
    self.is_text = True
