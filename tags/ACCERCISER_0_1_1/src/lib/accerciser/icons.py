'''
Defines a mapping from widget roles to icons representing them.

@author: Peter Parente
@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2006, 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import sys, os, glob
import gtk
import gobject
import wnck
from pyLinAcc.Constants import *

ICONS_PATH = os.path.join(sys.prefix, 'share', 
                          'accerciser', 'pixmaps', 'hicolor', '22x22')

if not os.path.exists(ICONS_PATH):
   ICONS_PATH = os.path.join(os.path.split(os.getcwd())[0], 'pixmaps')

role_to_icon = {
  ROLE_ACCELERATOR_LABEL : 'acceleratorlabel',
  ROLE_ALERT : 'alert', 
  ROLE_ANIMATION : 'animation', 
  ROLE_APPLICATION : 'desktopframe', # Temporary
  ROLE_ARROW : 'grip', # Temporary
  ROLE_AUTOCOMPLETE : 'combobox', # Temporary
  ROLE_CALENDAR : 'calendar',
  ROLE_CANVAS : 'canvas',
  ROLE_CAPTION : 'helpballoon', # Temporary
  ROLE_CHART : 'chart',
  ROLE_CHECK_BOX : 'checkbox', 
  ROLE_CHECK_MENU_ITEM : 'checkbox', # Temporary
  ROLE_COLOR_CHOOSER : 'colorchooser', 
  ROLE_COLUMN_HEADER : 'column', 
  ROLE_COMBO_BOX : 'combobox', 
  ROLE_DATE_EDITOR : 'calendar', # Temporary
  ROLE_DESKTOP_FRAME : 'desktopframe',
  ROLE_DESKTOP_ICON : 'desktopicon', 
  ROLE_DIAL : 'dial', 
  ROLE_DIALOG : 'desktopframe', # Temporary
  ROLE_DIRECTORY_PANE : 'directorypane', 
  ROLE_DOCUMENT_FRAME : 'filler', # Temporary
  ROLE_DRAWING_AREA : 'drawingarea',
  ROLE_EDITBAR : 'combobox', # Temporary
  ROLE_EMBEDDED : 'embedded', 
  ROLE_ENTRY : 'entry', 
  ROLE_EXTENDED : 'filler', # Temporary
  ROLE_FILE_CHOOSER : 'filechooser',
  ROLE_FILLER : 'filler', 
  ROLE_FOCUS_TRAVERSABLE : 'filler', # Temporary
  ROLE_FONT_CHOOSER : 'fontchooser',
  ROLE_FOOTER : 'label', # Temporary
  ROLE_FRAME : 'filler', # Temporary
  ROLE_GLASS_PANE : 'drawingarea', # Temporary
  ROLE_HEADER : 'label', # Temporary
  ROLE_HEADING : 'heading', 
  ROLE_HTML_CONTAINER : 'filler',
  ROLE_ICON : 'imagemap', # Temporary
  ROLE_IMAGE : 'image', 
  ROLE_INTERNAL_FRAME : 'filler', # Temporary
  ROLE_INVALID : 'invalid',
  ROLE_LABEL : 'label',
  ROLE_LAYERED_PANE : 'drawingarea', # Temporary
  ROLE_LIST : 'list',
  ROLE_LIST_ITEM : 'listitem', 
  ROLE_MENU : 'menuitem',  # Temporary
  ROLE_MENU_BAR : 'menuitem', # Temporary
  ROLE_MENU_ITEM : 'menuitem',
  ROLE_OPTION_PANE : 'filler', # Temporary
  ROLE_PAGE : 'filler', # Temporary
  ROLE_PAGE_TAB : 'label', 
  ROLE_PAGE_TAB_LIST : 'filler', # Temporary
  ROLE_PANEL : 'filler', # Temporary  
  ROLE_PARAGRAPH : 'filler', # Temporary  
  ROLE_PASSWORD_TEXT : 'passwordtext', # Temporary  
  ROLE_POPUP_MENU : 'menuitem',  # Temporary  
  ROLE_PROGRESS_BAR : 'progressbar',
  ROLE_PUSH_BUTTON : 'pushbutton', 
  ROLE_RADIO_BUTTON : 'pushbutton', # Temporary  
  ROLE_RADIO_MENU_ITEM : 'pushbutton', # Temporary  
  ROLE_ROOT_PANE : 'filler', # Temporary  
  ROLE_ROW_HEADER : 'row', # Temporary  
  ROLE_RULER : 'ruler', 
  ROLE_SCROLL_BAR : 'scrollbar', 
  ROLE_SCROLL_PANE : 'scrollpane',
  ROLE_SECTION : '', # Temporary  
  ROLE_SEPARATOR: 'seperator',
  ROLE_SLIDER : 'slider', 
  ROLE_SPIN_BUTTON : 'spinbutton', 
  ROLE_SPLIT_PANE : 'splitpane',
  ROLE_STATUS_BAR : 'statusbar',
  ROLE_TABLE : 'table', 
  ROLE_TABLE_CELL : 'tablecell', 
  ROLE_TABLE_COLUMN_HEADER : 'column', # Temporary
  ROLE_TABLE_ROW_HEADER : 'row', # Temporary
  ROLE_TEAROFF_MENU_ITEM : 'menuitem', # Temporary
  ROLE_TERMINAL : 'character', # Temporary
  ROLE_TEXT : 'character', # Temporary
  ROLE_TOGGLE_BUTTON : 'checkbox', # Temporary
  ROLE_TOOL_BAR : 'toolbar', 
  ROLE_TOOL_TIP : 'tooltip',
  ROLE_TREE : 'tree', 
  ROLE_TREE_TABLE : 'treetable',
  ROLE_UNKNOWN : 'filler', # Temporary
  ROLE_VIEWPORT : 'filler', # Temporary
  ROLE_WINDOW : 'desktopframe' # Temporary
}


def getIcon(acc):
  '''
  Loads an icon for the given application or accessible widget. Tries to use
  the current theme or wnck to get application icons. Uses icons from 
  at-poke for widgets.
  '''
  theme = gtk.icon_theme_get_default()
  try:
    role_name = acc.getRoleName()
    role = acc.getRole()
    if role_name == 'application':
      # try the theme first
      try:
        return theme.load_icon(acc.name, 24, gtk.ICON_LOOKUP_USE_BUILTIN)
      except gobject.GError:
        pass
      # then try wnck
      s = wnck.screen_get_default()
      s.force_update()
      for win in s.get_windows():
        wname = win.get_name()
        for child in acc:
          if child.name == wname:
            return win.get_mini_icon()
      return None
    else:
      # try using the role map or collapsing spaces
      name = role_to_icon.get(role) or role_name.replace(' ', '')
      try:
        fn = os.path.join(ICONS_PATH, '%s.png' % name)
        return gtk.gdk.pixbuf_new_from_file(fn)
      except gobject.GError:
        pass
  except Exception, e:
    pass
  fn = os.path.join(ICONS_PATH, 'filler.png')
  return gtk.gdk.pixbuf_new_from_file(fn)
