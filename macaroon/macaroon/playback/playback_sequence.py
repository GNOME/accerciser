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

import gobject

class SequenceStep:
  delta_time = 0

class AtomicAction(SequenceStep):
  def __init__(self, delta_time, func, *args, **kwargs):
    self.delta_time = delta_time
    self._func = func
    self._args = args
  def __call__(self):
    return self._func(*self._args)

class CallableAction(AtomicAction):
  def __init__(self, func, *args, **kwargs):
    AtomicAction.__init__(self, 0, func, *args, **kwargs)

class WaitAction(SequenceStep):
  def __init__(self, timeout):
    self._timeout = timeout
  def __call__(self):
    self.listenFor()
    self.wait()
  def listenFor(self):
    pass
  def wait(self):
    gobject.timeout_add(self._timeout, self._onTimeout)
    self.loop = gobject.MainLoop()
    self.loop.run()
  def _onTimeout(self):
    self.endWait()
    return False
  def endWait(self):
    if self.loop.is_running():
      self.loop.quit()

class MacroSequence(list):
  def __init__(self, embedded_loop=False):
    self._embedded_loop = embedded_loop
    self._loop = None
  def start(self):
    self._iterAction()
    if self._embedded_loop:
      self._loop = gobject.MainLoop()
      self._loop.run()
  def _iterAction(self):
    if len(self) == 0:
      if self._loop is not None:
        self._loop.quit()
      return
    action = self.pop(0)
    gobject.timeout_add(action.delta_time, self._doAction, action)
  def _doAction(self, action):
    action()
    self._iterAction()
    return False

def sample(arg):
  print arg


if __name__ == "__main__":
  sequence = MacroSequence(True)
  sequence.append(AtomicAction(0, sample, 'Ugly world 1'))
  sequence.append(AtomicAction(1000, sample, 'Ugly world 2'))
  sequence.append(AtomicAction(1000, sample, 'Ugly world 3'))
  sequence.append(WaitAction(1000))
  sequence.append(AtomicAction(1000, sample, 'Ugly world 5'))
  sequence.append(AtomicAction(1000, sample, 'Ugly world 6'))
  sequence.start()
