import sys
from time import sleep, time
import wnck
import gtk
from re import split
import pyLinAcc

sleep_time = 0.2

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

class Focus:
  def __init__(self):
    self.current_app = None
    self.current_frame = None
    self.node = pyLinAcc.Registry.getDesktop(0)
    window_list = []
    try_limit = 50
    while not window_list and try_limit:
      gtk.main_iteration(False)
      wnck_screen = wnck.screen_get_default()
      window_list = wnck_screen.get_windows_stacked()
      try_limit -= 1
    if not try_limit and not self.window_list:
      raise RuntimeError('Could not get window list')
    self.apps = set([w.get_application() for w in window_list])
  def application(self, app_name):
    for app in self.apps:
      if app.get_name() == app_name:
        self.current_app = app
        return True
    return False
  def frame(self, frame_name):
    if not self.current_app:
      raise Exception('No application was focused')
    for window in self.current_app.get_windows():
      if window.get_name() == frame_name:
        self.current_frame = window
        self.current_frame.activate(0)
        gtk.main_iteration(False)
        return True
    return False
  def _findAcc(self, acc_name):
    for child in self.node:
      if child.name == acc_name:
        self.node = child
        return True
    return False
    

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
    sleep(sleep_time)
    eg.generateKeyboardEvent(key_code, '', pyLinAcc.Constants.KEY_PRESS)
  sleep(sleep_time)
  eg.generateKeyboardEvent(_charToKeySym(finalKey), 
                           '', pyLinAcc.Constants.KEY_SYM)
  for key_code in modifiers:
    sleep(sleep_time)
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
    sleep(sleep_time)
    eg.generateKeyboardEvent(key, '', pyLinAcc.Constants.KEY_SYM)
    
focus = Focus()
