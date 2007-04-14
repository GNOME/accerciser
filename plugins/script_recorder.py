import os.path
from accerciser.plugin import ViewportPlugin
import pyLinAcc
import gtk
import gtksourceview
import threading
import wnck
from accerciser.i18n import N_

MODIFIERS = ['Control_L', 'Control_R',
             'Alt_L', 'Alt_R',
             'Shift_L', 'Shift_R',]

class ScriptRecorder(ViewportPlugin):
  plugin_name = N_('Script Recorder')
  plugin_description = N_('Creates dogtail style scripts')
  
  def init(self):
    text_buffer = gtksourceview.SourceBuffer()
    lm = gtksourceview.SourceLanguagesManager()
    lang = lm.get_language_from_mime_type('text/x-python')
    text_buffer.set_language(lang)
    text_buffer.set_highlight(True)
    text_buffer.set_text('#!/usr/bin/python\n\n'
                         'from accerciser.script_playback import *\n\n')
    self.text_view = gtksourceview.SourceView(text_buffer)
    self.text_view.set_editable(True)
    self.text_view.set_cursor_visible(True)
    button_box = gtk.HButtonBox()
    button_callbacks = (self._onRecord,
                        self._onClear, self._onSave)
    button_labels = (gtk.STOCK_MEDIA_RECORD, 
                     gtk.STOCK_CLEAR, gtk.STOCK_SAVE)
    for cb, label in zip(button_callbacks, button_labels):
      button = gtk.Button(label)
      button.set_use_stock(True)
      button_box.pack_start(button)
      button.connect('clicked', cb)
    button_box.set_layout(gtk.BUTTONBOX_START)
    vbox = gtk.VBox()
    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, 
                  gtk.POLICY_AUTOMATIC)
    sw.set_shadow_type(gtk.SHADOW_IN)
    sw.add(self.text_view)
    vbox.pack_start(sw)
    vbox.pack_end(button_box, False, False)
    self.plugin_area.add(vbox)
    self.mark = text_buffer.create_mark('scroll_mark', 
                                        text_buffer.get_end_iter(),
                                        False)
    self.event_manager = pyLinAcc.Event.Manager()
    self.typed_text = ''
    self.app_name = ''
    self.frame_name = ''
    

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

  def _onKeyPress(self, event):
    if event.any_data[0] in MODIFIERS or \
          event.any_data[0].startswith('ISO'):
      return
    if event.any_data[1] & (1 << pyLinAcc.Constants.MODIFIER_ALT):
      modifier = '<Alt>'
    elif event.any_data[1] & (1 << pyLinAcc.Constants.MODIFIER_CONTROL):
      modifier = '<Ctrl>'
    else:
      modifier = ''
    key = event.any_data[0]
    if not modifier and gtk.gdk.keyval_to_unicode(event.detail1):
      self.typed_text += unichr(gtk.gdk.keyval_to_unicode(event.detail1))
    else:
      if self.app_name:
        self.appendText('focus.application("%s")\n' % self.app_name)
        self.app_name = ''
      if self.frame_name:
        self.appendText('focus.frame("%s")\n' % self.frame_name)
        self.frame_name = ''
      if self.typed_text:
        self.appendText('type("%s")\n' % self.typed_text)
        self.typed_text = ''
      self.appendText('keyCombo("%s%s")\n' % (modifier, key))

  def _onWindowActivate(self, event):
    if self.isMyApp(event.source):
      return
    app = event.source.getApplication()
    if app:
      self.app_name = app.name
    self.frame_name = event.source.name

  def _onRecord(self, button):
    if button.get_label() == 'gtk-media-record':
      button.set_label(gtk.STOCK_MEDIA_STOP)
      self.event_manager.addClient(self._onKeyPress, 'keyboard:press')
      self.event_manager.addClient(self._onWindowActivate, 'window:activate')
    elif button.get_label() == 'gtk-media-stop':
      button.set_label(gtk.STOCK_MEDIA_RECORD)
      self.event_manager.removeClient(self._onKeyPress, 'keyboard:press')
      self.event_manager.removeClient(self._onWindowActivate, 'window:activate')

  def _onClear(self, button):
    self.app_name = ''
    self.frame_name = ''
    self.typed_text = ''
    text_buffer = self.text_view.get_buffer()
    text_buffer.set_text('#!/usr/bin/python\n\n'
                         'from accerciser.script_playback import *\n\n')

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
