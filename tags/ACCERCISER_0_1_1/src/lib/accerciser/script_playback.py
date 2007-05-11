import sys
from time import sleep, time
import wnck
import gobject, gtk
from re import split
import pyLinAcc
import os

keystroke_interval = 0.2
focus_timeout = 5

eg = pyLinAcc.Registry.getDeviceEventController()

_keymap = gtk.gdk.keymap_get_default()

ModifierKeyCodes = {
  'Control_L' : _keymap.get_entries_for_keyval(gtk.keysyms.Control_L)[0][0],
  'Alt_L' : _keymap.get_entries_for_keyval(gtk.keysyms.Alt_L)[0][0],
  'Shift_L' : _keymap.get_entries_for_keyval(gtk.keysyms.Shift_L)[0][0]
  }

keySymAliases = {
    'enter' : 'Return',
    'esc' : 'Escape',
    'alt' : 'Alt_L',
    'control' : 'Control_L',
    'ctrl' : 'Control_L',
    'shift' : 'Shift_L',
    'del' : 'Delete',
    'ins' : 'Insert',
    'pageup' : 'Page_Up',
    'pagedown' : 'Page_Down',
    ' ' : 'space',
    '\t' : 'Tab',
    '\n' : 'Return'
}

class _WindowManager:
  def __init__(self):
    self.loop = None
    self.screen = wnck.screen_get_default()
  def getApp(self, app_name):
    self.loop = gobject.MainLoop()
    self.returned_app = None
    self.screen.connect('application-opened', self._onAppOpened, app_name)
    gobject.idle_add(self._onIdleGetApp, app_name)
    gobject.timeout_add(focus_timeout*1000, self.loop.quit)
    self.loop.run()
    return self.returned_app
  def _onIdleGetApp(self, app_name):
    for window in self.screen.get_windows():
      app = window.get_application()
      if app.get_name() == app_name:
        self.returned_app = app
        self.loop.quit()
    return False
  def _onAppOpened(self, screen, app, app_name):
    if app.get_name() == app_name:
      self.returned_app = app
      self.loop.quit()
  def focusFrame(self, app, frame_name):
    window = None
    for w in app.get_windows():
      if w.get_name() == frame_name:
        window = w
        break
    if not window:
      return False
    window.activate(0)
    self.loop = gobject.MainLoop()
    self.activate_success = False
    self.screen.connect('active-window-changed', 
                        self._onWindowActivated, window)
    gobject.idle_add(self._onIdleFocus, window)
    gobject.timeout_add(focus_timeout*1000, self.loop.quit)
    self.loop.run()
  def _onIdleFocus(self, window):
    if self.screen.get_active_window() == window:
      self.activate_success = True
      self.loop.quit()
  def _onWindowActivated(self, screen, window):
    if self.screen.get_active_window() == window:
      self.activate_success = True
      self.loop.quit()


class Focus:
  def __init__(self):
    self.current_app = None
    self.current_frame = None
    self.node = pyLinAcc.Registry.getDesktop(0)
    self.wm = _WindowManager()
    self.dialog = self.frame

  def application(self, app_name):
    self.current_app = self.wm.getApp(app_name)
    success = bool(self.current_app)
    return success

  def frame(self, frame_name):
    if not self.current_app: return False
    self.current_frame = self.wm.focusFrame(self.current_app, frame_name)
    success = bool(self.current_frame)
    return success

def keyCombo(keystring):
  key_combo = []
  for key in split('[<>]', keystring):
    if key:
      key = keySymAliases.get(key.lower(), key)
      key_combo.append(key)
  pressKeys(key_combo)


def pressKeys(keys):
  modifiers = map(ModifierKeyCodes.get, keys[:-1])
  finalKey = keys[-1]
  for key_code in modifiers:
    sleep(keystroke_interval)
    eg.generateKeyboardEvent(key_code, '', pyLinAcc.Constants.KEY_PRESS)
  sleep(keystroke_interval)
  eg.generateKeyboardEvent(_charToKeySym(finalKey), 
                           '', pyLinAcc.Constants.KEY_SYM)
  for key_code in modifiers:
    sleep(keystroke_interval)
    eg.generateKeyboardEvent(key_code, '', pyLinAcc.Constants.KEY_RELEASE)

def _charToKeySym(key):
  try:
    rv = gtk.gdk.unicode_to_keyval(ord(key))
  except:
    rv = getattr(gtk.keysyms, key)
  return rv

def type(text):
  text_syms = map(_charToKeySym, text)
  for key in text_syms:
    sleep(keystroke_interval)
    eg.generateKeyboardEvent(key, '', pyLinAcc.Constants.KEY_SYM)
    
focus = Focus()

def run(cmd, arguments = '', appName=''):
  if arguments:
    args = arguments.split(' ')
  else:
    args = []
  pid = os.spawnlp(os.P_NOWAIT, cmd, cmd, *args)
  focus.application(appName or cmd)
  return pid
