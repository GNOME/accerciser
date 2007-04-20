import os.path
from accerciser.plugin import ViewportPlugin
import pyLinAcc
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
  intepreter_line = '#!/usr/bin/python'
  import_line = ''
  MODIFIERS = [keysyms.Control_L, keysyms.Control_R, 
               keysyms.Alt_L, keysyms.Alt_R, 
               keysyms.Super_L, keysyms.Super_R,
               keysyms.Shift_L, keysyms.Shift_R]
               
  def __init__(self):
      self.commands_queue = Queue()
      self.app_name = ''
      self.frame_name = ''

  def scriptCommand(self, event):
    if (event.type.klass, event.type.major) == ('window', 'activate'):
      return self._windowActivate(event)
    elif (event.type.klass, event.type.major) == ('keyboard', 'press'):
      return self._keyPress(event)

  def _keyPress(self, event):
    pass

  def _windowActivate(self, event):
    app = event.source.getApplication()
    if app:
      self.app_name = app.name
    self.frame_name = event.source.name

class DogtailFactory(ScriptFactory):
  import_line = 'from dogtail.procedural import *'
  def __init__(self):
    ScriptFactory.__init__(self)
    self.typed_text = ''

  def _keyPress(self, event):
    if event.detail1 in self.MODIFIERS or \
          event.any_data[0].startswith('ISO'):
      return
    if event.any_data[1] in (0, gtk.gdk.SHIFT_MASK) and \
          gtk.gdk.keyval_to_unicode(event.detail1):
      self.typed_text += unichr(gtk.gdk.keyval_to_unicode(event.detail1))
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
                                       gtk.accelerator_name(event.detail1,
                                                            event.any_data[1]))


class NativeFactory(DogtailFactory):
  import_line = 'from accerciser.script_playback import *'

class LDTPFactory(DogtailFactory):
  import_line = 'from ldtp import *'
  def __init__(self):
    ScriptFactory.__init__(self)
    self.typed_text = ''

  def _keyPress(self, event):
    if event.detail1 in self.MODIFIERS or \
          event.any_data[0].startswith('ISO'):
      return
    if event.any_data[1] in (0, gtk.gdk.SHIFT_MASK) and \
          gtk.gdk.keyval_to_unicode(event.detail1):
      self.typed_text += unichr(gtk.gdk.keyval_to_unicode(event.detail1))
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
                                       gtk.accelerator_name(event.detail1,
                                                            event.any_data[1]))
class ScriptRecorder(ViewportPlugin):
  plugin_name = N_('Script Recorder')
  plugin_description = N_('Creates dogtail style scripts')
  
  def init(self):
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
    self.event_manager = pyLinAcc.Event.Manager()
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

  def close(self):
    self.event_manager.close()

  def _onRecord(self, button):
    if button.get_label() == 'gtk-media-record':
      button.set_label(gtk.STOCK_MEDIA_STOP)
      self.event_manager.addClient(self._onEvent, 
                                   'keyboard:press', 'window:activate')
    elif button.get_label() == 'gtk-media-stop':
      button.set_label(gtk.STOCK_MEDIA_RECORD)
      self.event_manager.removeClient(self._onEvent, 
                                      'keyboard:press', 'window:activate')

  def _onEvent(self, event):
    if event.source and self.isMyApp(event.source):
      return
    self.script_factory.scriptCommand(event)
    while self.script_factory.commands_queue.qsize():
      self.appendText(self.script_factory.commands_queue.get_nowait())

  def _onClear(self, button):
    if self._askLoseChanges():
      self._clearBuffer()

  def _onTypeToggled(self, radio_button, factory_class):
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
    text_buffer = self.text_view.get_buffer()
    text_buffer.set_text('%s\n\n%s\n\n' % \
                           (self.script_factory.intepreter_line,
                            self.script_factory.import_line))
    text_buffer.set_modified(False)

  def _askLoseChanges(self):
    text_buffer = self.text_view.get_buffer()
    if not text_buffer.get_modified():
      return True
    dialog = gtk.MessageDialog(self.get_toplevel(), 0, gtk.MESSAGE_WARNING,
                               gtk.BUTTONS_OK_CANCEL,
                               _('The current script will be lost.'))
    response_id = dialog.run()
    dialog.destroy()
    if response_id == gtk.RESPONSE_OK:
      return True
    else:
      return False
    

  def _onSave(self, button):
    save_dialog = gtk.FileChooserDialog('Save recorded script',
                                        action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                                 gtk.STOCK_OK, gtk.RESPONSE_OK))
    save_dialog.set_do_overwrite_confirmation(True)
    save_dialog.connect('response', self._onSaveResponse)
    save_dialog.set_default_response(gtk.RESPONSE_OK)
    save_dialog.show_all()

  def _onSaveResponse(self, filechooser, response):
    if response == gtk.RESPONSE_OK:
      save_to = open(filechooser.get_filename(), 'w')
      text_buffer = self.text_view.get_buffer()
      save_to.write(text_buffer.get_text(text_buffer.get_start_iter(),
                                         text_buffer.get_end_iter()))
      save_to.close()
    filechooser.destroy()
