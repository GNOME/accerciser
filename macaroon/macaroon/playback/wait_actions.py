'''
Actions used for waiting for something or for a certain time.

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

from gi.repository import GLib
import pyatspi

import re

from .sequence_step import SequenceStep
from . import utils
import sys

_ = lambda x: x

class WaitAction(SequenceStep):
  '''
  Base class for all wait actions.

  @ivar wait_for: List of events to wait for.
  @type wait_for: list of string
  @ivar _acc_name: Name of source accessible of events we are waiting for.
  @type _acc_name: string
  @ivar _acc_path: Tree path in application to source accessible.
  @type _acc_path: list of integer
  @ivar _acc_role: Role of source accessible.
  @type _acc_role: integer
  @ivar _timeout: Time to wait in milliseconds before timing out.
  @type _timeout: integer
  '''
  def __init__(self, event, acc_name, acc_path, acc_role, timeout):
    '''
    Initialize a L{WaitAction}

    @param event: Event to wait for
    @type event: string
    @param acc_name: Name of source accessible of events we are waiting for.
    @type acc_name: string
    @param acc_path: Tree path in application to source accessible.
    @type acc_path: list of integer
    @param acc_role: Role of source accessible.
    @type acc_role: integer
    @param timeout: Time to wait in milliseconds before timing out.
    @type timeout: integer
    '''
    SequenceStep.__init__(self)
    if isinstance(event, list):
      self.wait_for = event
    else:
      self.wait_for = [event]
    self._acc_name = acc_name
    self._acc_path = acc_path
    self._acc_role = acc_role
    self._timeout = timeout

  def __call__(self, cached_events):
    '''
    Called when an insance is "called".

    @param cached_events: List of events that have been cached since the
    last sequence step.
    @type cached_events: list of Accessibility.Event
    '''
    if self.wait_for == []: return
    self._cached_events = cached_events
    if self.checkExistingState(): return
    pyatspi.Registry.registerEventListener(self.onEvent, *self.wait_for)
    GLib.timeout_add(self._timeout, self._onTimeout)

  def checkExistingState(self):
    '''
    Check to see if perhaps the event we are waiting for has already been fired
    before this instance has been created.

    @return: True if the event has already occured.
    @rtype: boolean
    '''
    if not self.done:
      for event in self._cached_events:
        self.onEvent(event)
    return self.done

  def _onTimeout(self):
    '''
    Timout callback.
    '''
    if not self.done:
      sys.stderr.write('Macaroon timeout: %s\n' % self)
    self.stepDone()
    return False

  def onEvent(self, event):
    '''
    Event callback.

    @param event: Event that has triggered this callback.
    @type event: Accessibility.Event
    '''
    if (self._acc_name is None or \
          self._acc_name == event.source.name) and \
       (self._acc_path is None or \
          self._acc_path == pyatspi.getPath(event.source)) and \
       (self._acc_role is None or \
          self._acc_role == event.source.getRole()):
      self.stepDone()

  def stepDone(self):
    '''
    Done with this sequence step. Deregister event listeners.
    '''
    if not self.done:
      pyatspi.Registry.deregisterEventListener(self.onEvent, *self.wait_for)
    return SequenceStep.stepDone(self)

  def __str__(self):
    '''
    String representation of instance.

    @return: String representation of instance.
    @rtype: string
    '''
    return 'Wait for %s' % ','.join(self.wait_for)

class WaitForWindowActivate(WaitAction):
  '''
  Wait for a window to become activated.

  @todo: Eitan: Provide the ability to match regular expressions since frame
  titles are highly dynamic.

  @ivar _frame_re: Window name to match.
  @type _frame_re: string
  @ivar _application_re: Application name to match, or None if no
  matching needs to be performed.
  @type _application_re: string
  '''
  def __init__(self, frame_re, application_re=None, timeout=30000):
    '''
    Initialize L{WaitForWindowActivate}.

    @param frame_re: Window name to match.
    @type frame_re: string
    @param application_re: Application name to match, or None if no
    matching needs to be performed.
    @type application_re: string
    @param timeout: Time to wait in milliseconds before timing out.
    @type timeout: integer
    '''
    WaitAction.__init__(self,
                        ['window:activate',
                         'object:property-change:accessible-name'],
                        None, None, None, timeout)
    self._frame_re = frame_re
    self._application_re = application_re

  def checkExistingState(self):
    '''
    Check if the window we are waiting for is already activated.

    @return: True if window is already activated.
    @rtype: boolean
    '''
    self._active_frame = utils.getActiveFrame()
    if self.isRightFrame(self._active_frame):
      self.stepDone()
    return WaitAction.checkExistingState(self)

  def onEvent(self, event):
    '''
    Event callback. Check if this is the fame we are looking for and
    move to the next step.
    '''
    if event.type == 'window:activate' or \
          (event.type == 'object:property-change:accessible-name' and \
             event.source == self._active_frame):
      self._active_frame = event.source
      if self.isRightFrame(self._active_frame):
        self.stepDone()

  def isRightFrame(self, acc):
    '''
    Check if this is the frame we are waiting for.

    @param acc: Frame accessible.
    @type acc: Accessibility.Accessible

    @return: True if this is the right frame.
    @rtype: boolean
    '''
    return acc is not None and \
      (acc.name == self._frame_re or \
      re.compile(self._frame_re and self._frame_re or "").match(acc.name))

  def __str__(self):
    '''
    String representation of instance.

    @return: String representation of instance.
    @rtype: string
    '''
    return _('Wait for window %s to get activated') % self._frame_re

class WaitForFocus(WaitAction):
  '''
  Wait for a focus event.
  '''
  def __init__(self, acc_name=None,
               acc_path=None, acc_role=None, timeout=10000):
    '''
    Initialize a L{WaitForFocus}

    @param acc_name: Name of source accessible of events we are waiting for.
    @type acc_name: string
    @param acc_path: Tree path in application to source accessible.
    @type acc_path: list of integer
    @param acc_role: Role of source accessible.
    @type acc_role: integer
    @param timeout: Time to wait in milliseconds before timing out.
    @type timeout: integer
    '''
    WaitAction.__init__(self, "focus:", acc_name, acc_path, acc_role, timeout)

  def __str__(self):
    '''
    String representation of instance.

    @return: String representation of instance.
    @rtype: string
    '''
    if self._acc_name and self._acc_role:
      identifier = '%s called "%s"' % \
          (repr(self._acc_role).replace('ROLE_','').lower().replace('_',' '),
           self._acc_name)
    elif self._acc_name:
      identifier = self._acc_name
    elif self._acc_role:
      identifier = \
          repr(self._acc_role).replace('ROLE_','').lower().replace('_',' ')
    elif self._acc_path:
      identifier = 'componenet at %s' % self._acc_path
    else:
      identifier = 'anything'
    return _('Wait for %s to be focused') % identifier

class WaitForDocLoad(WaitAction):
  '''
  Wait for a document to load.
  '''
  def __init__(self):
    '''
    Initialize L{WaitForDocLoad}
    '''
    WaitAction.__init__(self, 'document:load-complete',
                        None, None, None, 30000)
  def __str__(self):
    '''
    String representation of instance.

    @return: String representation of instance.
    @rtype: string
    '''
    return 'Wait for document to load'
