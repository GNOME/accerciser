'''
Keypress actions.

@author: Eitan Isaacson
@copyright: Copyright (c) 2007 Eitan Isaacson
@license: GPL

This file may be distributed and/or modified under the terms of the GNU General
Public License version 2 as published by the Free Software Foundation. This file
is distributed without any warranty; without even the implied warranty of
merchantability or fitness for a particular purpose.

See "COPYING" in the source distribution for more information.

Headers in this file shall remain intact.
'''

from gi.repository import GObject
from gi.repository import GLib
import pyatspi
import sys
from .wait_actions import WaitAction
from os import environ
_ = lambda x: x

class MacroSequence(GObject.GObject):
  '''
  Sequence class. Holds a list of steps and performs them in order.
  Waits for each step to emit a "done" signal. And performs the next step
  only after it's delta time has lapsed. Emits "step-done" each time a step
  is completed.

  @ivar _loop: Loop instance if the main loop should be embedded.
  @type _loop: GLib.MainLoop
  @ivar _verbose: Print to standard output the current step the sequence is in.
  @type _verbose: boolean
  @ivar _current_step: The index of the currently performed step.
  @type _current_step: integer
  @ivar _current_handler: Event handler ID of currently performed step.
  @type _current_handler: integer
  @ivar steps: List of sequence steps to perform.
  @type steps: list of L{SequenceStep}
  @ivar _anticipated_event_types: List of event types we should be on the lookout
  for.
  @type _anticipated_event_types: list of string
  @ivar _anticipated_events: Events that we have anticipated, and that have
  came through.
  @type _anticipated_events: list of Accessibility.Accessible
  '''
  __gsignals__ = {'step-done' : (GObject.SignalFlags.RUN_FIRST,
                                 None, (GObject.TYPE_INT,))}
  def __init__(self):
    '''
    Initialize L{MacroSequence}.
    '''
    super(MacroSequence, self).__init__()
    self._loop = None
    self._verbose = False
    self._current_step = 0
    self._current_handler = 0
    self.steps = []
    self._anticipated_event_types = []
    self._anticipated_events = []

  def append(self, step):
    '''
    Add a new sequence step to the end of the sequence.

    @param step: A sequence step to add.
    @type step: L{SequenceStep}
    '''
    self.steps.append(step)

  def start(self, embedded_loop=True, verbose=False):
    '''
    Start sequence.

    @param embedded_loop: Embed a loop in the sequnce, if we are running this
    outside of a main loop.
    @type embedded_loop: boolean
    '''
    self._verbose = bool(verbose or environ.get('MACAROON_VERBOSE', 0))
    self._iterAction()
    if embedded_loop:
      self._loop = GLib.MainLoop()
      self._loop.run()

  def _iterAction(self):
    '''
    Iterate to the next sequence step.
    '''
    if len(self.steps) <= self._current_step:
      if self._loop is not None:
        self._loop.quit()
      return
    action = self.steps[self._current_step]
    if self._verbose:
      print(_('SEQUENCE: %s') % action)

    try:
      next_action = self.steps[self._current_step + 1]
    except IndexError:
      next_action = None

    pyatspi.Registry.deregisterEventListener(self._onAnticipatedEvent,
                                             *self._anticipated_event_types)
    if isinstance(next_action, WaitAction):
      self._anticipated_event_types = next_action.wait_for
    else:
      self._anticipated_event_types = []
    pyatspi.Registry.registerEventListener(self._onAnticipatedEvent,
                                           *self._anticipated_event_types)
    self._current_handler = action.connect('done', self._onStepDone)

    GLib.timeout_add(action.delta_time, self._doAction, action)

  def _onAnticipatedEvent(self, event):
    '''
    Callback for antibitaed events, keep them for the next sequence step which
    might be a L{WaitAction} .

    @param event: Event that was recieved.
    @type event: Accessibility.Event
    '''
    self._anticipated_events.append(event)

  def _onStepDone(self, action):
    '''
    Callback for when a step is done.

    @param action: Step that has finished.
    @type action: L{SequenceStep}
    '''
    action.disconnect(self._current_handler)
    self.emit('step-done', self._current_step)
    self._current_step += 1
    self._iterAction()

  def _doAction(self, action):
    '''
    Perform the action.

    @param action: Step to perform.
    @type action: L{SequenceStep}
    '''
    if isinstance(action, WaitAction):
      action(self._anticipated_events)
      self._anticipated_events = []
    else:
      action()
    return False
