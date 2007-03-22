'''
Event monitor plugin.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''
import gtk
import pyLinAcc
import gobject
import os.path
import gettext, os, sys, locale
from Queue import Queue, Empty
import accerciser.plugin
from accerciser.tools import Tools
from accerciser.i18n import _
import pango
from gtk import keysyms, gdk

GLADE_FILE = os.path.join(os.path.dirname(__file__), 
                          'event_monitor.glade')

class EventMonitor(accerciser.plugin.ViewportPlugin):
  '''
  Class for the monitor viewer.
  '''
  plugin_name = 'Event monitor'
  plugin_description = 'Shows events as they occur from selected types and sources'
  COL_NAME = 0
  COL_FULL_NAME = 1
  COL_TOGGLE = 2
  COL_INCONSISTENT = 3

  def init(self):
    self.global_hotkeys = [('Highlight last event entry', 
                            self._onHighlightEvent,
                            keysyms.L, gdk.MOD1_MASK | gdk.SHIFT_MASK)]
    self.source_filter = None
    self.main_xml = gtk.glade.XML(GLADE_FILE, 'event_monitor_vbox')
    vbox = self.main_xml.get_widget('event_monitor_vbox')
    self.plugin_area.add(vbox)
    self.event_manager = pyLinAcc.Event.Manager()
    self.event_manager.addClient(self._onHotKey, 'keyboard:press')
    self._initTreeView()
    self._popEventsModel()
    self._initTextView()

    self.monitor_toggle = self.main_xml.get_widget('monitor_toggle')

    self.listen_list = []
    self.timeout_id = gobject.timeout_add(100, self._onFlushQueue)
    self.event_queue = Queue()

    self.main_xml.signal_autoconnect(self)
    self.show_all()

  def _popEventsModel(self):
    events = pyLinAcc.Constants.event_tree.keys()
    for sub_events in pyLinAcc.Constants.event_tree.itervalues():
      events.extend(sub_events)
    events = list(set([event.strip(':') for event in events]))
    events.sort()
    self._appendChildren(None, '', 0, events)

  def onAccChanged(self, acc):
    pass

  def _initTreeView(self):
    self.events_model = gtk.TreeStore(str,  # COL_NAME
                                      str, # COL_FULL_NAME
                                      bool, # COL_TOGGLE  
                                      bool) # COL_INCONSISTENT
    event_tree = self.main_xml.get_widget('treeview_events')
    event_tree.set_model(self.events_model)
    crt = gtk.CellRendererText()
    crc = gtk.CellRendererToggle()
    crc.connect('toggled', self._onToggled)
    tvc = gtk.TreeViewColumn(_('Name'))
    tvc.pack_start(crc, True)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crc, 
                       active=self.COL_TOGGLE,
                       inconsistent=self.COL_INCONSISTENT)
    tvc.set_attributes(crt, text=self.COL_NAME)
    event_tree.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Full name'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=self.COL_FULL_NAME)
    event_tree.append_column(tvc)

  def _initTextView(self):
    self.textview_monitor = self.main_xml.get_widget('textview_monitor')
    
    self.monitor_buffer = self.textview_monitor.get_buffer()
    self.monitor_mark = \
        self.monitor_buffer.create_mark('scroll_mark', 
                                        self.monitor_buffer.get_end_iter(),
                                        False)
    self.monitor_buffer.create_mark('mark_last_log', 
                                    self.monitor_buffer.get_end_iter(),
                                    True)
    self.monitor_buffer.create_tag('last_log', weight=700)

  def _appendChildren(self, parent_iter, parent, level, events):
    for event in events:
      if event.count(':') == level and event.startswith(parent):
        iter = self.events_model.append(parent_iter, 
                                        [event.split(':')[-1],
                                         event, False, False])
        self._appendChildren(iter, event, level + 1, events)
        
  def _onToggled(self, renderer_toggle, path):
    iter = self.events_model.get_iter(path)
    val = not self.events_model.get_value(iter, self.COL_TOGGLE)
    self._iterToggle(iter, val)
    self._resetClient()

  def _resetClient(self):
    self.event_manager.removeClient(self._handleAccEvent, *self.listen_list)
    self.listen_list = self._getEnabledEvents(self.events_model.get_iter_root())
    if self.monitor_toggle.get_active():
      self.event_manager.addClient(self._handleAccEvent, *self.listen_list)

  def _getEnabledEvents(self, iter):
    listen_for = []
    while iter:
      toggled = self.events_model.get_value(iter, self.COL_TOGGLE)
      inconsistent = self.events_model.get_value(iter, self.COL_INCONSISTENT)
      if toggled and not inconsistent:
        listen_for.append(self.events_model.get_value(iter, self.COL_FULL_NAME))
      elif inconsistent:
        listen_for_child = self._getEnabledEvents(self.events_model.iter_children(iter))
        listen_for.extend(listen_for_child)
      iter = self.events_model.iter_next(iter)
    return listen_for

  def _iterToggle(self, iter, val):
    self.events_model.set_value(iter, self.COL_INCONSISTENT, False)
    self.events_model.set_value(iter, self.COL_TOGGLE, val)
    self._setAllDescendants(iter, val)
    parent = self.events_model.iter_parent(iter)
    while parent:
      is_consistent = self._descendantsConsistent(parent)
      self.events_model.set_value(parent, 
                                  self.COL_INCONSISTENT,
                                  not is_consistent)
      self.events_model.set_value(parent, self.COL_TOGGLE, val)
      parent = self.events_model.iter_parent(parent)
  
  def _setAllDescendants(self, iter, val):
    child = self.events_model.iter_children(iter)
    while child:
      self.events_model.set_value(child, self.COL_TOGGLE, val)
      self._setAllDescendants(child, val)
      child = self.events_model.iter_next(child)
  
  def _descendantsConsistent(self, iter):
    child = self.events_model.iter_children(iter)
    if child:
      first_val = self.events_model.get_value(child, self.COL_TOGGLE)
    while child:
      child_val = self.events_model.get_value(child, self.COL_TOGGLE)
      is_consistent = self._descendantsConsistent(child)
      if (first_val != child_val or not is_consistent):
        return False
      child = self.events_model.iter_next(child)
    return True

  def _onSelectAll(self, widget):
    iter = self.events_model.get_iter_root()
    while iter:
      self._iterToggle(iter, True)
      iter = self.events_model.iter_next(iter)
    self._resetClient()

  def _onClearSelection(self, widget):
    iter = self.events_model.get_iter_root()
    while iter:
      self._iterToggle(iter, False)
      iter = self.events_model.iter_next(iter)
    self._resetClient()


  def _onFlushQueue(self):
    while True:
      try:
        event = self.event_queue.get_nowait()
      except Empty:
        break
      iter = self.monitor_buffer.get_iter_at_mark(self.monitor_mark)
      self.monitor_buffer.move_mark_by_name(
        'mark_last_log', 
        self.monitor_buffer.get_iter_at_mark(self.monitor_mark))
      self._insertEventIntoBuffer(event)
      self.textview_monitor.scroll_mark_onscreen(self.monitor_mark)
    return True

  def _insertEventIntoBuffer(self, event):
    if event.source:
      self._writeText('%s(%s, %s, %s)\n\tsource: ' % \
                        (event.type.asString(), event.detail1, 
                         event.detail2, event.any_data))
      hyperlink = self._createHyperlink(event.source)
      self._writeText(str(event.source), hyperlink)
      self._writeText('\n\tapplication: ')
      try:
        app = event.source.getApplication()
      except:
        app = None
      hyperlink = self._createHyperlink(app)
      self._writeText(str(app), hyperlink)
      self._writeText('\n')
    else:
      self.monitor_buffer.insert(
        self.monitor_buffer.get_iter_at_mark(self.monitor_mark),
        str(event)+'\n')

  def _writeText(self, text, *tags):
    if tags:
      self.monitor_buffer.insert_with_tags(
        self.monitor_buffer.get_iter_at_mark(self.monitor_mark),
        text, *tags)
    else:
      self.monitor_buffer.insert(
        self.monitor_buffer.get_iter_at_mark(self.monitor_mark),
        text)

  def _createHyperlink(self, acc):
    hyperlink = self.monitor_buffer.create_tag(
      None, 
      foreground='blue',
      underline=pango.UNDERLINE_SINGLE)
    hyperlink.connect('event', self._onLinkClicked)
    hyperlink.set_data('acc', acc)
    hyperlink.set_data('islink', True)
    return hyperlink

  def _onLinkClicked(self, tag, widget, event, iter):
    if event.type == gtk.gdk._2BUTTON_PRESS and event.button == 1:
      self.node.update(tag.get_data('acc'))

  def _onLinkKeyPress(self, textview, event):
    if event.keyval in (gtk.keysyms.Return, 
                        gtk.keysyms.KP_Enter,
                        gtk.keysyms.space):
      buffer = textview.get_buffer()
      iter = buffer.get_iter_at_mark(buffer.get_insert())
      acc = None
      for tag in iter.get_tags():
        acc = tag.get_data('acc')
        if acc:
          self.node.update(acc)
          break

  def _onLinkMotion(self, textview, event):
    x, y = textview.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET,
                                             int(event.x), int(event.y))
    iter = textview.get_iter_at_location(x, y)
    cursor = gtk.gdk.Cursor(gtk.gdk.XTERM)
    for tag in iter.get_tags():
      if tag.get_data('islink'):
        cursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
        break
    textview.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(cursor)
    textview.window.get_pointer()
    return False

  def _handleAccEvent(self, event):
    if self.isMyApp(event.source) or not self._eventFilter(event):
      return
    self.event_queue.put(event)

  def _onSave(self, widget):
    save_dialog = gtk.FileChooserDialog('Save monitor output',
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
      save_to.write(self.monitor_buffer.get_text(self.monitor_buffer.get_start_iter(),
                                             self.monitor_buffer.get_end_iter()))
      save_to.close()
    filechooser.destroy()

  def _onClear(self, widget):
    self.monitor_buffer.set_text('')

  
  def _onMonitorToggled(self, monitor_toggle):
    if monitor_toggle.get_active():
      self.event_manager.addClient(self._handleAccEvent, *self.listen_list)
    else:
      self.event_manager.removeClient(self._handleAccEvent, *self.listen_list)

  def _onSourceToggled(self, radio_button):
    self.source_filter = radio_button.get_name()

  def _eventFilter(self, event):
    if self.source_filter == 'source_app':
      if (hasattr(event.source, 'getApplication') and
          hasattr(self.acc, 'getApplication')):
        return event.source.getApplication() == self.acc.getApplication()
      else:
        return False
    elif self.source_filter == 'source_acc':
      return event.source == self.acc
    else:
      return True

  def _onHotKey(self, event):
    pass
  
  def _onHighlightEvent(self):
    self._onFlushQueue()
    start_iter = self.monitor_buffer.get_iter_at_mark(
      self.monitor_buffer.get_mark('mark_last_log'))
    end_iter = self.monitor_buffer.get_end_iter()
    self.monitor_buffer.apply_tag_by_name('last_log', start_iter, end_iter)

  def close(self):
    self.event_manager.close()
