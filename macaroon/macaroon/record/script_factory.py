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

from gtk import keysyms
import gtk
from Queue import Queue
from time import time
import pyatspi

class ScriptFactory(object):
  '''
  Abstract class for a script factory. Classes of specific platforms like
  dogtail are derived from this.

  @cvar intepreter_line: The top intepreter line
  @type intepreter_line: string
  @cvar import_line: The import line for the specific platform
  @type import_line: strin
  @cvar terminate_line: A line that terminates a certain segment of a script.
  @type terminate_line: strin
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
  terminate_line = ''
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

class SequenceFactory(ScriptFactory):
  import_line = \
      'from macaroon.playback.keypress_mimic import *\n\nsequence = MacroSequence()'
  terminate_line = 'sequence.start()'
  def __init__(self):
    '''
    Initialize the object.
    '''
    ScriptFactory.__init__(self)
    self._time = 0
  def _getDelta(self):
    current_time = time()
    delta = current_time - self._time
    self._time = current_time
    if delta == current_time: delta = 0
    return int(delta*1000)

class Level2SequenceFactory(SequenceFactory):
  def __init__(self):
    SequenceFactory.__init__(self)
    self.typed_text = ''
    self.last_focused = None
    self.frame_name = ''

  def keyPressCommand(self, event):
    if event.id in self.MODIFIERS or \
          event.event_string.startswith('ISO'):
      return
    if event.modifiers in (0, gtk.gdk.SHIFT_MASK) and \
          gtk.gdk.keyval_to_unicode(event.id):
      self.typed_text += unichr(gtk.gdk.keyval_to_unicode(event.id))
    else:
      if self.frame_name:
        self.commands_queue.put_nowait(
          'sequence.append(WaitForWindowActivate("%s",None))\n' % \
            self.frame_name)
        self.frame_name = ''
      if self.last_focused:
        self.commands_queue.put_nowait('# "%s"\n' % self.last_focused.name)
        self.commands_queue.put_nowait(
          '#sequence.append(WaitForFocus        (%s, pyatspi.%s))\n' % \
            (pyatspi.getPath(self.last_focused), 
             repr(self.last_focused.getRole())))
        self.last_focused = None
      if self.typed_text:
        self.commands_queue.put_nowait(
          'sequence.append(TypeAction           ("%s"))\n' % \
                                         self.typed_text)
        self.typed_text = ''
      self.commands_queue.put_nowait(
        'sequence.append(KeyComboAction         ("%s"))\n' % \
          gtk.accelerator_name(event.id, event.modifiers))

  def focusCommand(self, event):
    self.last_focused = event.source

  def windowActivateCommand(self, event):
    self.frame_name = event.source.name

class Level1SequenceFactory(SequenceFactory):
  def keyPressCommand(self, event):
    delta = self._getDelta()
    self.commands_queue.put_nowait(
      'sequence.append(KeyPressAction       (%5d,%4d)) # Press %s\n' % \
        (delta, event.hw_code, event.event_string))
  def keyReleaseCommand(self, event):
    delta = self._getDelta()
    self.commands_queue.put_nowait(
      'sequence.append(KeyReleaseAction     (%5d,%4d)) # Release %s\n' % \
        (delta, event.hw_code, event.event_string))
  def windowActivateCommand(self, event):
    self.commands_queue.put_nowait(
      'sequence.append(WaitForWindowActivate("%s",None))\n' % \
        event.source.name)
  def focusCommand(self, event):
    self.commands_queue.put_nowait('# "%s"\n' % event.source.name)
    self.commands_queue.put_nowait(
      '#sequence.append(WaitForFocus(%s,pyatspi.%s))\n' % \
        (pyatspi.getPath(event.source), repr(event.source.getRole())))

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
