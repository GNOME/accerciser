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
import gi

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
from gi.repository import Pango

import pyatspi
import os.path
import gettext, os, sys, locale
from accerciser.plugin import ViewportPlugin
from accerciser.i18n import _, N_, DOMAIN
from accerciser import node

UI_FILE = os.path.join(os.path.dirname(__file__),
                       'event_monitor.ui')

class EventMonitor(ViewportPlugin):
  '''
  Class for the monitor viewer.

  @ivar source_filter: Determines what events from what sources could be shown.
  Either source_app and source_acc for selected applications and accessibles
  respectively. Or everything.
  @type source_filter: string
  @ivar main_xml: The main event monitor gtkbuilder file.
  @type main_xml: gtk.GtkBuilder
  @ivar monitor_toggle: Toggle button for turining monitoring on and off.
  @type monitor_toggle: gtk.ToggleButton
  @ivar listen_list: List of at-spi events the monitor is currently listening
  to.
  @type listen_list: list
  @ivar events_model: Data model of all at-spi event types.
  @type events_model: gtk.TreeStore
  @ivar textview_monitor: Text view of eent monitor.
  @type textview_monitor: gtk.TextView
  @ivar monitor_buffer: Text buffer for event monitor.
  @type monitor_buffer: gtk.TextBuffer
  '''
  plugin_name = N_('Event Monitor')
  plugin_name_localized = _(plugin_name)
  plugin_description = \
      N_('Shows events as they occur from selected types and sources')
  COL_NAME = 0
  COL_FULL_NAME = 1
  COL_TOGGLE = 2
  COL_INCONSISTENT = 3

  def init(self):
    '''
    Initialize the event monitor plugin.
    '''
    self.global_hotkeys = [(N_('Highlight last event entry'),
                            self._onHighlightEvent,
                            gdk.KEY_e, gdk.ModifierType.MOD1_MASK | \
                                       gdk.ModifierType.CONTROL_MASK),
                           (N_('Start/stop event recording'),
                            self._onStartStop,
                            gdk.KEY_r, gdk.ModifierType.MOD1_MASK | \
                                       gdk.ModifierType.CONTROL_MASK),
                           (N_('Clear event log'),
                            self._onClearlog,
                            gdk.KEY_t, gdk.ModifierType.MOD1_MASK | \
                                       gdk.ModifierType.CONTROL_MASK)]

    self.source_filter = None
    self.main_xml = gtk.Builder()
    self.main_xml.set_translation_domain(DOMAIN)
    self.main_xml.add_from_file(UI_FILE)
    vpaned = self.main_xml.get_object('monitor_vpaned')
    self.plugin_area.add(vpaned)
    self.events_model = self.main_xml.get_object('events_treestore')
    self._popEventsModel()
    self._initTextView()

    self.monitor_toggle = self.main_xml.get_object('monitor_toggle')

    self.source_filter = None
    self.sources_dict = { \
        self.main_xml.get_object('source_everthing') : 'source_everthing', \
        self.main_xml.get_object('source_app') : 'source_app', \
        self.main_xml.get_object('source_acc') : 'source_acc' \
    }

    self.listen_list = []

    self.node.connect('accessible-changed', self._onNodeUpdated)

    self.main_xml.connect_signals(self)
    self.show_all()

  def _onStartStop(self):
    active = self.monitor_toggle.get_active()
    self.monitor_toggle.set_active(not active)

  def _onClearlog(self):
    self.monitor_buffer.set_text('')

  def _onNodeUpdated(self, node, acc):
    if acc == node.desktop and \
          self.source_filter in ('source_app', 'source_acc'):
      self.monitor_toggle.set_active(False)

  def _popEventsModel(self):
    '''
    Populate the model for the event types tree view. Uses a constant
    from pyatspi for the listing of all event types.
    '''
    events = list(pyatspi.EVENT_TREE.keys())
    for sub_events in pyatspi.EVENT_TREE.values():
      events.extend(sub_events)
    events = list(set([event.strip(':') for event in events]))
    events.sort()
    GLib.idle_add(self._appendChildren, None, '', 0, events)

  def _initTextView(self):
    '''
    Initialize text view in monitor plugin.
    '''
    self.textview_monitor = self.main_xml.get_object('textview_monitor')

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
    '''
    Append child events to a parent event's iter.

    @param parent_iter: The tree iter of the parent.
    @type parent_iter: gtk.TreeIter
    @param parent: The parent event.
    @type parent: string
    @param level: The generation of the children.
    @type level: integer
    @param events: A list of children
    @type events: list

    @return: Return false to that this won't be called again in the mainloop.
    @rtype: boolean
    '''
    for event in events:
      if event.count(':') == level and event.startswith(parent):
        iter = self.events_model.append(parent_iter,
                                        [event.split(':')[-1],
                                         event, False, False])
        GLib.idle_add(self._appendChildren, iter, event, level + 1, events)
    return False

  def _onToggled(self, renderer_toggle, path):
    '''
    Callback for toggled events in the treeview.

    @param renderer_toggle: The toggle cell renderer.
    @type renderer_toggle: gtk.CellRendererToggle
    @param path: The path of the toggled node.
    @type path: tuple
    '''
    iter = self.events_model.get_iter(path)
    val = not self.events_model.get_value(iter, self.COL_TOGGLE)
    self._iterToggle(iter, val)
    self._resetClient()

  def _resetClient(self):
    '''
    De-registers the client from the currently monitored events.
    If the monitor is still enabled it get's a list of enabled events
    and re-registers the client.
    '''
    pyatspi.Registry.deregisterEventListener(self._handleAccEvent,
                                             *self.listen_list)
    self.listen_list = self._getEnabledEvents(self.events_model.get_iter_first())
    if self.monitor_toggle.get_active():
      pyatspi.Registry.registerEventListener(self._handleAccEvent,
                                             *self.listen_list)

  def _getEnabledEvents(self, iter):
    '''
    Recursively walks through the events model and collects all enabled
    events in a list.

    @param iter: Iter of root node to check under.
    @type iter: gtk.TreeIter

    @return: A list of enabled events.
    @rtype: list
    '''
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
    '''
    Toggle the given node. If the node has children toggle them accordingly
    too. Toggle all anchester nodes too, either true, false or inconsistent,
    sepending on the value of their children.

    @param iter: Iter of node to toggle.
    @type iter: gtk.TreeIter
    @param val: Toggle value.
    @type val: boolean
    '''
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
    '''
    Set all descendants of a given node to a certain toggle value.

    @param iter: Parent node's iter.
    @type iter: gtk.TreeIter
    @param val: Toggle value.
    @type val: boolean
    '''
    child = self.events_model.iter_children(iter)
    while child:
      self.events_model.set_value(child, self.COL_TOGGLE, val)
      self._setAllDescendants(child, val)
      child = self.events_model.iter_next(child)

  def _descendantsConsistent(self, iter):
    '''
    Determine if all of a node's descendants are consistently toggled.

    @param iter: Parent node's iter.
    @type iter: gtk.TreeIter

    @return: True if descendants nodes are consistent.
    @rtype: boolean
    '''
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

  def _onSelectAll(self, button):
    '''
    Callback for "select all" button. Select all event types.

    @param button: Button that was clicked
    @type button: gtk.Button
    '''
    iter = self.events_model.get_iter_first()
    while iter:
      self._iterToggle(iter, True)
      iter = self.events_model.iter_next(iter)
    self._resetClient()

  def _onClearSelection(self, button):
    '''
    Callback for "clear selection" button. Clear all selected events.

    @param button: Button that was clicked.
    @type button: gtk.Button
    '''
    iter = self.events_model.get_iter_first()
    while iter:
      self._iterToggle(iter, False)
      iter = self.events_model.iter_next(iter)
    self._resetClient()

  def _logEvent(self, event):
    '''
    Log the given event.

    @param event: The event to log.
    @type event: Accessibility.Event
    '''
    iter = self.monitor_buffer.get_iter_at_mark(self.monitor_mark)
    self.monitor_buffer.move_mark_by_name(
      'mark_last_log',
      self.monitor_buffer.get_iter_at_mark(self.monitor_mark))
    self._insertEventIntoBuffer(event)
    self.textview_monitor.scroll_mark_onscreen(self.monitor_mark)

  def _insertEventIntoBuffer(self, event):
    '''
    Inserts given event in to text buffer. Creates hyperlinks for
    the events context accessibles.

    @param event: The at-spi event we are inserting.
    @type event: Accessibility.Event
    '''
    ts = int((os.times()[-1] * 10 ) % 1000)
    self._writeText('%02.1f %s(%s, %s, %s)\n\tsource: ' % \
                      (ts / 10, event.type, event.detail1,
                        event.detail2, event.any_data))
    hyperlink = self._createHyperlink(event.source)
    self._writeText(str(event.source), hyperlink)
    self._writeText('\n\tapplication: ')
    hyperlink = self._createHyperlink(event.host_application)
    self._writeText(str(event.host_application), hyperlink)
    if hasattr(event, "sender") and event.sender != event.host_application:
        self._writeText('\n\tsender: ')
        hyperlink = self._createHyperlink(event.sender)
        self._writeText(str(event.sender), hyperlink)
    self._writeText('\n')
    if event.type == "screen-reader:region-changed":
        try:
            text = event.source.queryText()
            (x, y, width, height) = text.getRangeExtents(event.detail1, event.detail2, pyatspi.DESKTOP_COORDS)
            if width > 0 and height > 0:
                ah = node._HighLight(x, y, width, height,
                                     node.FILL_COLOR, node.FILL_ALPHA,
                                     node.BORDER_COLOR, node.BORDER_ALPHA,
                                     2.0, 0)
                ah.highlight(node.HL_DURATION)
        except:
            pass

  def _writeText(self, text, *tags):
    '''
    Convenience function for inserting text in to the text buffer.
    If tags are provided they are applied to the inserted text.

    @param text: Text to insert
    @type text: string
    @param *tags: List of optional tags to insert with text
    @type *tags: list of gtk.TextTag
    '''
    if tags:
      self.monitor_buffer.insert_with_tags(
        self.monitor_buffer.get_iter_at_mark(self.monitor_mark),
        text, *tags)
    else:
      self.monitor_buffer.insert(
        self.monitor_buffer.get_iter_at_mark(self.monitor_mark),
        text)

  def _createHyperlink(self, acc):
    '''
    Create a hyperlink tag for a given accessible. When the link is clicked
    the accessible is selected in the main program.

    @param acc: The accessible to create the tag for.
    @type acc: Accessibility.Accessible

    @return: The new hyperlink tag
    @rtype: gtk.TextTag
    '''
    hyperlink = self.monitor_buffer.create_tag(
      None,
      underline=Pango.Underline.SINGLE)
    hyperlink.connect('event', self._onLinkClicked)
    setattr(hyperlink, 'acc', acc)
    setattr(hyperlink, 'islink', True)
    return hyperlink

  def _onLinkClicked(self, tag, widget, event, iter):
    '''
    Callback for clicked link. Select links accessible in main application.

    @param tag: Tag that was clicked.
    @type tag: gtk.TextTag
    @param widget: The widget that received event.
    @type widget: gtk.Widget
    @param event: The event object.
    @type event: gdk.Event
    @param iter: The text iter that was clicked.
    @type iter: gtk.TextIter
    '''
    if event.type == gdk.EventType.BUTTON_RELEASE and \
           event.button.button == 1 and not self.monitor_buffer.get_has_selection():
      self.node.update(getattr(tag, 'acc'))

  def _onLinkKeyPress(self, textview, event):
    '''
    Callback for a keypress in the text view. If the keypress is enter or
    space, and the cursor is above a link, follow it.

    @param textview: Textview that was pressed.
    @type textview: gtk.TextView
    @param event: Event object.
    @type event: gdk.Event
    '''
    if event.keyval in (gdk.KEY_Return,
                        gdk.KEY_KP_Enter,
                        gdk.KEY_space):
      buffer = textview.get_buffer()
      iter = buffer.get_iter_at_mark(buffer.get_insert())
      acc = None
      for tag in iter.get_tags():
        acc = getattr(tag, 'acc')
        if acc:
          self.node.update(acc)
          break

  def _onLinkMotion(self, textview, event):
    '''
    Change mouse cursor shape when hovering over a link.

    @param textview: Monitors text view.
    @type textview: gtk.TextView
    @param event: Event object
    @type event: gdk.Event

    @return: Return False so event continues in callback chain.
    @rtype: boolean
    '''
    x, y = textview.window_to_buffer_coords(gtk.TextWindowType.WIDGET,
                                             int(event.x), int(event.y))
    isText = True
    iter = textview.get_iter_at_location(x, y)
    if isinstance(iter, tuple):
        (isText, iter) = iter
    cursor = gdk.Cursor(gdk.CursorType.XTERM)
    if isText:
      for tag in iter.get_tags():
        if getattr(tag, 'islink'):
          cursor = gdk.Cursor(gdk.CursorType.HAND2)
          break
    window = textview.get_window(gtk.TextWindowType.TEXT)
    window.set_cursor(cursor)
    return False

  def _handleAccEvent(self, event):
    '''
    Main at-spi event client. If event passes filtering requirements, log it.

    @param event: The at-spi event recieved.
    @type event: Accessibility.Event
    '''
    if self.isMyApp(event.source) or not self._eventFilter(event):
      return
    self._logEvent(event)

  def _onSave(self, button):
    '''
    Callback for 'save' button clicked. Saves the buffer in to the given
    filename.

    @param button: Button that was clicked.
    @type button: gtk.Button
    '''
    save_dialog = gtk.FileChooserNative.new(
      _('Save monitor output'),
      self.get_toplevel(),
      gtk.FileChooserAction.SAVE,
      _('_OK'),
      _('_Cancel'))
    save_dialog.set_do_overwrite_confirmation(True)
    response = save_dialog.run()
    if response == gtk.ResponseType.ACCEPT:
      save_to = open(save_dialog.get_filename(), 'w')
      save_to.write(
        self.monitor_buffer.get_text(self.monitor_buffer.get_start_iter(),
                                     self.monitor_buffer.get_end_iter(), False))
      save_to.close()
    save_dialog.destroy()

  def _onClear(self, button):
    '''
    Callback for 'clear' button. Clears monitor's text buffer.

    @param button: Button that was clicked.
    @type button: gtk.Button
    '''
    self.monitor_buffer.set_text('')


  def _onMonitorToggled(self, monitor_toggle):
    '''
    Callback for monitor toggle button. Activates or deactivates monitoring.

    @param monitor_toggle: The toggle button that was toggled.
    @type monitor_toggle: gtk.ToggleButton
    '''
    if monitor_toggle.get_active():
      pyatspi.Registry.registerEventListener(self._handleAccEvent,
                                             *self.listen_list)
    else:
      pyatspi.Registry.deregisterEventListener(self._handleAccEvent,
                                               *self.listen_list)

  def _onSourceToggled(self, radio_button):
    '''
    Callback for radio button selection for choosing source filters.

    @param radio_button: Radio button that was selected.
    @type radio_button: gtk.RadioButton
    '''
    self.source_filter = self.sources_dict[radio_button]

  def _eventFilter(self, event):
    '''
    Determine if an event's source should make the event filtered.

    @param event: The given at-spi event.
    @type event: Accessibility.Event

    @return: False if the event should be filtered.
    @rtype: boolean
    '''
    if self.source_filter == 'source_app':
      try:
        return event.source.getApplication() == self.acc.getApplication()
      except:
        return False
    elif self.source_filter == 'source_acc':
      return event.source == self.acc
    else:
      return True

  def _onHighlightEvent(self):
    '''
    A callback fom a global key binding. Makes the last event in the textview
    bold.
    '''
    start_iter = self.monitor_buffer.get_iter_at_mark(
      self.monitor_buffer.get_mark('mark_last_log'))
    end_iter = self.monitor_buffer.get_end_iter()
    self.monitor_buffer.apply_tag_by_name('last_log', start_iter, end_iter)
