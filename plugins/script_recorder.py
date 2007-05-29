import os.path
from accerciser.plugin import ViewportPlugin
import pyatspi
import gtk
from gtk import keysyms
import gtksourceview
import threading
import wnck
from accerciser.i18n import N_, _
from Queue import Queue

GLADE_FILE = os.path.join(os.path.dirname(__file__), 
                          'script_recorder.glade')

class ScriptFactory(object):
  '''
  Abstract class for a script factory. Classes of specific platforms like
  dogtail are derived from this.

  @cvar intepreter_line: The top intepreter line
  @type intepreter_line: string
  @cvar import_line: The import line for the specific platform
  @type import_line: strin
  @cvar MODIFIERS: Key symbols that are considered modifiers.
  @type MODIFIERS: list

  @ivar commands_queue: The commands that are being produced by the facory.
  @type commands_queue: Queue.Queue
  @ivar app_name: The last focused application name
  @type app_name: string
  @ivar frame_name: The last focused window frame name.
  @type frame_name: string.
  '''
  intepreter_line = '#!/usr/bin/python'
  import_line = ''
  MODIFIERS = [keysyms.Control_L, keysyms.Control_R, 
               keysyms.Alt_L, keysyms.Alt_R, 
               keysyms.Super_L, keysyms.Super_R,
               keysyms.Shift_L, keysyms.Shift_R]
               
  def __init__(self):
    '''
    Initialize the script factory.
    '''
    self.commands_queue = Queue()
    self.app_name = ''
    self.frame_name = ''

  def keyPressCommand(self, event):
    '''
    Processing key presses in to commands
    
    @param event: The keypress at-spi event.
    @type event: Accessibility.DeviceEvent
    '''
    pass

  def windowActivateCommand(self, event):
    '''
    Store the focus event source's application name and frame name.
    
    @param event: The at-spi focus event.
    @type event: Accessibility.Event
    '''
    app = event.source.getApplication()
    if app:
      self.app_name = app.name
    self.frame_name = event.source.name

class DogtailFactory(ScriptFactory):
  '''
  Script factory for dogtail scripts.

  @ivar typed_text: Plain text that has been typed so far.
  @type typed_text: string
  '''
  import_line = 'from dogtail.procedural import *'
  def __init__(self):
    '''
    Initialize the object.
    '''
    ScriptFactory.__init__(self)
    self.typed_text = ''

  def keyPressCommand(self, event):
    '''
    Create command lines for variuos key presses.
    
    @param event: Key press at-spi event.
    @type event: Accessibility.DeviceEvent
    '''
    if event.id in self.MODIFIERS or \
          event.event_string.startswith('ISO'):
      return
    if event.modifiers in (0, gtk.gdk.SHIFT_MASK) and \
          gtk.gdk.keyval_to_unicode(event.id):
      self.typed_text += unichr(gtk.gdk.keyval_to_unicode(event.id))
    else:
      if self.app_name:
        self.commands_queue.put_nowait('focus.application("%s")\n' % \
                                         self.app_name)
        self.app_name = ''
      if self.frame_name:
        self.commands_queue.put_nowait('focus.frame("%s")\n' % \
                                         self.frame_name)
        self.frame_name = ''
      if self.typed_text:
        self.commands_queue.put_nowait('type("%s")\n' % \
                                         self.typed_text)
        self.typed_text = ''
      self.commands_queue.put_nowait('keyCombo("%s")\n' % \
                                       gtk.accelerator_name(event.id,
                                                            event.modifiers))


class NativeFactory(DogtailFactory):
  '''
  Script factory for native scripts. Besides the import line, 
  it should be identical to dogtail scripts.
  '''
  import_line = 'from accerciser.script_playback import *'

class LDTPFactory(DogtailFactory):
  '''
  Script factory for LDTP scripts.

  @ivar typed_text: Plain text that has been typed so far.
  @type typed_text: string
  '''
  import_line = 'from ldtp import *'
  def __init__(self):
    '''
    Initialize the object.
    '''
    ScriptFactory.__init__(self)
    self.typed_text = ''

  def keyPressCommand(self, event):
    '''
    Create command lines for variuos key presses.
    
    @param event: Key press at-spi event.
    @type event: Accessibility.DeviceEvent
    '''
    if event.id in self.MODIFIERS or \
          event.event_string.startswith('ISO'):
      return
    if event.modifiers in (0, gtk.gdk.SHIFT_MASK) and \
          gtk.gdk.keyval_to_unicode(event.id):
      self.typed_text += unichr(gtk.gdk.keyval_to_unicode(event.id))
    else:
      if self.frame_name:
        self.commands_queue.put_nowait('waittillguiexist("%s")\n' % \
                                         self.frame_name)
        self.frame_name = ''
      if self.typed_text:
        self.commands_queue.put_nowait('generatekeyevent("%s")\n' % \
                                         self.typed_text)
        self.typed_text = ''
      self.commands_queue.put_nowait('generatekeyevent("%s")\n' % \
                                       gtk.accelerator_name(event.id,
                                                            event.modifiers))
class ScriptRecorder(ViewportPlugin):
  '''
  Script recorder plugin class.

  @ivar text_view: Script area text view.
  @type text_view: gtk.TextView
  @ivar mark: Scroll mark, keeps textview automatically srolling down.
  @type mark: gtk.TextMark
  @ivar script_factory: The selected script factory
  @type script_factory: L{ScriptFactory}
  @ivar last_active_type_button: The last active script type radio button.
  @type last_active_type_button: gtk.RadioButton
  '''
  plugin_name = N_('Script Recorder')
  plugin_name_localized = _(plugin_name)
  plugin_description = N_('Creates dogtail style scripts')
  
  def init(self):
    '''
    Initialize the plugin.
    '''
    text_buffer = gtksourceview.SourceBuffer()
    lm = gtksourceview.SourceLanguagesManager()
    lang = lm.get_language_from_mime_type('text/x-python')
    text_buffer.set_language(lang)
    text_buffer.set_highlight(True)
    self.text_view = gtksourceview.SourceView(text_buffer)
    self.text_view.set_editable(True)
    self.text_view.set_cursor_visible(True)
    xml = gtk.glade.XML(GLADE_FILE, 'main_vbox')
    vbox = xml.get_widget('main_vbox')
    sw =  xml.get_widget('textview_sw')
    sw.add(self.text_view)
    self.plugin_area.add(vbox)
    self.mark = text_buffer.create_mark('scroll_mark', 
                                        text_buffer.get_end_iter(),
                                        False)
    for radio_name, factory_class in (('radio_native', NativeFactory),
                                      ('radio_dogtail', DogtailFactory),
                                      ('radio_ldtp', LDTPFactory)):
      button = xml.get_widget(radio_name)
      handler_id = button.connect('toggled', 
                                  self._onTypeToggled, 
                                  factory_class)
      button.set_data('toggled_handler', handler_id)
      if button.get_active():
        self.script_factory = factory_class()
        self.last_active_type_button = button
    self._clearBuffer()
    xml.signal_autoconnect(self)
    self.plugin_area.show_all()

  def appendText(self, text):
    '''
    Appends the given text to the L{gtk.TextView} which in turn displays the 
    text in the plugins's console.

    @param text: Text to append.
    @type text: string
    '''
    text_buffer = self.text_view.get_buffer()
    text_buffer.insert(text_buffer.get_end_iter(), text)
    self.text_view.scroll_mark_onscreen(self.mark)

  def _onRecord(self, button):
    '''
    Callback for record button clicks. If the plugin is already recording 
    this callback is for the stop button.
    
    @param button: The clicked button.
    @type button: gtk.Button
    '''
    if button.get_label() == 'gtk-media-record':
      button.set_label(gtk.STOCK_MEDIA_STOP)
      pyatspi.Registry.registerEventListener(self._onWindowActivate, 
                                             'window:activate')
      masks = []
      mask = 0
      while mask <= (1 << pyatspi.MODIFIER_NUMLOCK):
        masks.append(mask)
        mask += 1
      pyatspi.Registry.registerKeystrokeListener(
        self._onKeystroke,
        mask=masks,
        kind=(pyatspi.KEY_PRESSED_EVENT,))
    elif button.get_label() == 'gtk-media-stop':
      button.set_label(gtk.STOCK_MEDIA_RECORD)
      pyatspi.Registry.deregisterEventListener(self._onWindowActivate, 
                                             'window:activate')
      masks = []
      mask = 0
      while mask <= (1 << pyatspi.MODIFIER_NUMLOCK):
        masks.append(mask)
        mask += 1
      pyatspi.Registry.deregisterKeystrokeListener(
        self._onKeystroke,
        mask=masks,
        kind=(pyatspi.KEY_PRESSED_EVENT,))

  def _onWindowActivate(self, event):
    '''
    Callback for window focus events. Calls the script factory and flushes
    it's queue.
    
    @param event: Focus at-spi event.
    @type event: Accessibility.Event
    '''
    if self.isMyApp(event.source):
      return
    self.script_factory.windowActivateCommand(event)
    while self.script_factory.commands_queue.qsize():
      self.appendText(self.script_factory.commands_queue.get_nowait())

  def _onKeystroke(self, event):
    '''
    Callback for key press events. Calls the script factory and flushes
    it's queue.
    
    @param event: Key press at-spi event.
    @type event: Accessibility.DeviceEvent
    '''
    self.script_factory.keyPressCommand(event)
    while self.script_factory.commands_queue.qsize():
      self.appendText(self.script_factory.commands_queue.get_nowait())

  def _onClear(self, button):
    '''
    Callback for 'clear' button press.
    
    @param button: Button that was clicked.
    @type button: gtk.Button
    '''
    if self._askLoseChanges():
      self._clearBuffer()

  def _onTypeToggled(self, radio_button, factory_class):
    '''
    Callback for script type radio buttons.
    
    @param radio_button: Radio button that was toggled.
    @type radio_button: gtk.RadioButton
    @param factory_class: Factory class that is associated with this button.
    @type factory_class: L{ScriptFactory}
    '''
    if not radio_button.get_active() or \
          radio_button is self.last_active_type_button:
      return
    if self._askLoseChanges():
      self.script_factory = factory_class()
      self._clearBuffer()
      self.last_active_type_button = radio_button
    else:
      self.last_active_type_button.set_active(True)

  def _clearBuffer(self):
    '''
    Clears the script text buffer and inserts the intepreter and import line.
    '''
    text_buffer = self.text_view.get_buffer()
    text_buffer.set_text('%s\n\n%s\n\n' % \
                           (self.script_factory.intepreter_line,
                            self.script_factory.import_line))
    text_buffer.set_modified(False)

  def _askLoseChanges(self):
    '''
    Raises a dialog that asks the user to confirm the loss of the current
    script in the buffer.
    
    @return: True if user confirms.
    @rtype: boolean
    '''
    text_buffer = self.text_view.get_buffer()
    if not text_buffer.get_modified():
      return True
    dialog = gtk.MessageDialog(self.get_toplevel(), 0, gtk.MESSAGE_WARNING,
                               gtk.BUTTONS_OK_CANCEL,
                               _('The current script will be lost.'))
    dialog.set_title(_('Confirm clear'))
    response_id = dialog.run()
    dialog.destroy()
    if response_id == gtk.RESPONSE_OK:
      return True
    else:
      return False
    

  def _onSave(self, button):
    '''
    Callback for 'save' button. Raises file chooser dialog for saving
    contents of script buffer.
    
    @param button: Button that was clicked.
    @type button: gtk.Button
    '''
    save_dialog = gtk.FileChooserDialog(
      'Save recorded script',
      action=gtk.FILE_CHOOSER_ACTION_SAVE,
      buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
               gtk.STOCK_OK, gtk.RESPONSE_OK))
    save_dialog.set_do_overwrite_confirmation(True)
    save_dialog.set_default_response(gtk.RESPONSE_OK)
    save_dialog.show_all()
    response = save_dialog.run()
    if response == gtk.RESPONSE_OK:
      save_to = open(save_dialog.get_filename(), 'w')
      text_buffer = self.text_view.get_buffer()
      save_to.write(text_buffer.get_text(text_buffer.get_start_iter(),
                                         text_buffer.get_end_iter()))
      save_to.close()
    save_dialog.destroy()
