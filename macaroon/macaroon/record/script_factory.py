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

import pyatspi
from queue import Queue
from time import time

class _CommandsQueue(Queue):
  def __init__(self):
    Queue.__init__(self)
    self.virgin = True
  def put(self, item, block=True, timeout=None):
    Queue.put(self, item, block, timeout)
    self.virgin = False

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
  intepreter_line = '#!/usr/bin/python3.2'
  import_line = ''
  MODIFIERS = [Gdk.KEY_Control_L, Gdk.KEY_Control_R,
               Gdk.KEY_Alt_L, Gdk.KEY_Alt_R,
               Gdk.KEY_Super_L, Gdk.KEY_Super_R,
               Gdk.KEY_Shift_L, Gdk.KEY_Shift_R]

  def __init__(self):
    '''
    Initialize the script factory.
    '''
    self.commands_queue = _CommandsQueue()
    self.app_name = ''
    self.frame_name = ''

  def keyPressCommand(self, event):
    '''
    Processing key presses in to commands

    @param event: The keypress at-spi event.
    @type event: Accessibility.DeviceEvent
    '''
    pass

  def keyReleaseCommand(self, event):
    '''
    Processing key releases in to commands

    @param event: The key release at-spi event.
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

  def focusCommand(self):
    pass

  def docLoadCommand(self):
    pass

  def terminateScript(self):
    self.commands_queue.virgin = True

class SequenceFactory(ScriptFactory):
  import_line = \
      'from macaroon.playback import *\n\nsequence = MacroSequence()'
  def __init__(self, wait_for_focus=False):
    '''
    Initialize the object.
    '''
    ScriptFactory.__init__(self)
    self._time = 0
    if wait_for_focus:
      self._focus_comment = ''
    else:
      self._focus_comment = '#'
  def _getDelta(self):
    current_time = time()
    delta = current_time - self._time
    self._time = current_time
    if delta == current_time: delta = 0
    return int(delta*1000)
  def terminateScript(self):
    self.commands_queue.put_nowait('\nsequence.start()\n')
    ScriptFactory.terminateScript(self)

class Level2SequenceFactory(SequenceFactory):
  def __init__(self, wait_for_focus=False):
    SequenceFactory.__init__(self, wait_for_focus)
    self.typed_text = ''
    self.last_focused = None
    self.frame_name = ''
    self._last_app = None

  def keyPressCommand(self, event):
    if event.id in self.MODIFIERS or \
          (event.event_string.startswith('ISO') and \
             event.event_string != 'ISO_Left_Tab'):
      return
    if isinstance(event, pyatspi.deviceevent.DeviceEvent):
      # If it's a fake one, then it is a global WM hotkey, no need for context.
      self._prependContext()
    if event.modifiers in (0, Gdk.ModifierType.SHIFT_MASK) and \
          Gdk.keyval_to_unicode(event.id):
      self.typed_text += chr(Gdk.keyval_to_unicode(event.id))
    else:
      if self.frame_name:
        if isinstance(event, pyatspi.deviceevent.DeviceEvent):
          self.commands_queue.put_nowait(
            'sequence.append(WaitForWindowActivate("%s", None))\n' % \
              self.frame_name.replace('"','\"'))
        self.frame_name = ''
      if self.last_focused:
        name, path, role = self.last_focused
        self.commands_queue.put_nowait(
            '%ssequence.append(WaitForFocus("%s", acc_role=pyatspi.%s))\n' % \
            (self._focus_comment, name.replace('"','\"'), repr(role)))
        self.last_focused = None
      if self.typed_text:
        self.commands_queue.put_nowait(
          'sequence.append(TypeAction("%s"))\n' % \
            self.typed_text.replace('"','\"'))
        self.typed_text = ''
      self.commands_queue.put_nowait(
        'sequence.append(KeyComboAction("%s"))\n' % \
          Gtk.accelerator_name(event.id, Gdk.ModifierType(event.modifiers)))

  def focusCommand(self, event):
    try:
      path = pyatspi.getPath(event.source)
    except RuntimeError:
      path = []
    self.last_focused = (event.source.name,
                         path,
                         event.source.getRole())

  def windowActivateCommand(self, event):
    app = event.source.getApplication()
    if app is None:
      self.frame_name = event.source.name
      return
    if self._last_app == app.name:
      return
    else:
      self._last_app = app.name
    self.frame_name = event.source.name

  def docLoadCommand(self):
    print('factory thing')
    self.commands_queue.put_nowait(
      'sequence.append(WaitForDocLoad())\n')

  def _prependContext(self):
    if not self.frame_name and self.commands_queue.virgin:
      self.frame_name = self._getActiveFrameName()
    if self.frame_name:
      self.commands_queue.put_nowait(
        'sequence.append(WaitForWindowActivate("%s",None))\n' % \
          self.frame_name)
      self.frame_name = ''


  def _getActiveFrameName(self):
    desktop = pyatspi.Registry.getDesktop(0)
    active_frame = None
    for app in desktop:
      if not app: continue
      for acc in app:
        if acc is None: continue
        if acc.getRole() == pyatspi.ROLE_FRAME:
          state_set = acc.getState()
          if state_set.contains(pyatspi.STATE_ACTIVE):
            active_frame = acc
          state_set.unref()
          if active_frame is not None:
            return active_frame.name
    return ''

  def terminateScript(self):
    if self.typed_text:
      self._prependContext()
      self.commands_queue.put_nowait(
        'sequence.append(TypeAction           ("%s"))\n' % self.typed_text)
    SequenceFactory.terminateScript(self)

class Level1SequenceFactory(SequenceFactory):
  def keyPressCommand(self, event):
    delta = self._getDelta()
    self.commands_queue.put_nowait(
      'sequence.append(KeyPressAction(%d, %d, "%s")) # Press %s\n' % \
        (delta, event.hw_code, event.event_string, event.event_string))
  def keyReleaseCommand(self, event):
    delta = self._getDelta()
    self.commands_queue.put_nowait(
      'sequence.append(KeyReleaseAction(%d, %d, "%s")) # Release %s\n' % \
        (delta, event.hw_code, event.event_string, event.event_string))
  def windowActivateCommand(self, event):
    self.commands_queue.put_nowait(
      'sequence.append(WaitForWindowActivate("%s", None))\n' % \
        event.source.name)
  def focusCommand(self, event):
    self.commands_queue.put_nowait(
      '%ssequence.append(WaitForFocus("%s", acc_role=pyatspi.%s))\n' % \
        (self._focus_comment, event.source.name,
         event.source.getRole().value_name.replace("ATSPI_", "")))

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
    if event.modifiers in (0, Gdk.ModifierType.SHIFT_MASK) and \
          Gdk.keyval_to_unicode(event.id):
      self.typed_text += chr(Gdk.keyval_to_unicode(event.id))
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
                                       Gtk.accelerator_name(event.id,
                                                            Gdk.ModifierType(event.modifiers)))


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
    if event.modifiers in (0, Gdk.ModifierType.SHIFT_MASK) and \
          Gdk.keyval_to_unicode(event.id):
      self.typed_text += chr(Gdk.keyval_to_unicode(event.id))
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
                                       Gtk.accelerator_name(event.id,
                                                            Gdk.ModifierType(event.modifiers)))
