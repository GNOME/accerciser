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

import gobject, pyatspi

class SequenceStep(gobject.GObject):
  __gsignals__ = {'done' : (gobject.SIGNAL_RUN_FIRST, 
                                 gobject.TYPE_NONE, ())}
  delta_time = 0
  def __init__(self):
    self.__gobject_init__()
    self.done = False
  def stepDone(self):
    if not self.done:
      self.done = True
      self.emit('done')
    return False

class AtomicAction(SequenceStep):
  def __init__(self, delta_time, func, *args, **kwargs):
    SequenceStep.__init__(self)
    self.delta_time = delta_time
    self._func = func
    self._args = args
  def __call__(self):
    self._func(*self._args)

class CallableAction(AtomicAction):
  def __init__(self, func, *args, **kwargs):
    AtomicAction.__init__(self, 0, func, *args, **kwargs)

class WaitAction(SequenceStep):
  wait_for = []
  def __init__(self, timeout):
    SequenceStep.__init__(self)
    self._timeout = timeout
  def __call__(self, cached_events):
    if self.wait_for == []: return
    self._cached_events = cached_events
    if self.checkExistingState(): return
    pyatspi.Registry.registerEventListener(self.onEvent, *self.wait_for)
    gobject.timeout_add(self._timeout, self._onTimeout)
  def checkExistingState(self):
    if not self.done:
      for event in self._cached_events:
        self.onEvent(event)
    return self.done
  def _onTimeout(self):
    self.stepDone()
    return False
  def onEvent(self, event):
    self.stepDone()
  def stepDone(self):
    if not self.done:
      pyatspi.Registry.deregisterEventListener(self.onEvent, *self.wait_for)
    return SequenceStep.stepDone(self)
  def __str__(self):
    return 'Wait for', ','.join(self.wait_for)

class MacroSequence(gobject.GObject):
  __gsignals__ = {'step-done' : (gobject.SIGNAL_RUN_FIRST, 
                                 gobject.TYPE_NONE, (gobject.TYPE_INT,))} 
  def __init__(self):
    self.__gobject_init__()
    self._loop = None
    self._current_step = 0
    self._current_handler = 0
    self.steps = []
    self._anticipated_event_types = []
    self._anticipated_events = []
  def append(self, step):
    self.steps.append(step)
  def start(self, embedded_loop=True):
    self._iterAction()
    if embedded_loop:
      self._loop = gobject.MainLoop()
      self._loop.run()
  def _iterAction(self):
    if len(self.steps) <= self._current_step:
      if self._loop is not None:
        self._loop.quit()
      return
    action = self.steps[self._current_step]

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

    gobject.timeout_add(action.delta_time, self._doAction, action)
  def _onAnticipatedEvent(self, event):
    self._anticipated_events.append(event)
  def _onStepDone(self, action):
    action.disconnect(self._current_handler)
    self.emit('step-done', self._current_step)
    self._current_step += 1
    self._iterAction()
  def _doAction(self, action):
    if isinstance(action, WaitAction):
      action(self._anticipated_events)
      self._anticipated_events = []
    else:
      action()
    return False
