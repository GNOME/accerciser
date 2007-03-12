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

GLADE_ICONS_PATH = os.path.join(sys.prefix, 'share', 
                                'glade3', 'pixmaps', '22x22')

ICONS_PATH = os.path.join(sys.prefix, 'share', 'accerciser', 'icons')

if not os.path.exists(ICONS_PATH):
   ICONS_PATH = os.path.join(os.path.split(os.getcwd())[0], 'icons')

role_to_icon = {
  ROLE_ACCELERATOR_LABEL : 'accellabel',
  ROLE_ALERT : 'messagedialog', 
  ROLE_ANIMATION : 'image', 
  ROLE_APPLICATION : 'gnomepropertybox',
  ROLE_ARROW : 'arrow', 
  ROLE_AUTOCOMPLETE : 'comboboxentry',
  ROLE_CALENDAR : 'calendar',
  ROLE_CANVAS : 'gnomecanvas',
  ROLE_CAPTION : 'label', 
  ROLE_CHART : 'curve',
  ROLE_CHECK_BOX : 'checkbutton', 
  ROLE_CHECK_MENU_ITEM : 'checkmenuitem',
  ROLE_COLOR_CHOOSER : 'colorselection', 
  ROLE_COLUMN_HEADER : 'label', 
  ROLE_COMBO_BOX : 'combobox', 
  ROLE_DATE_EDITOR : 'comboboxentry', 
  ROLE_DESKTOP_FRAME : 'gnomeiconlist',
  ROLE_DESKTOP_ICON : 'gnomeiconentry', 
  ROLE_DIAL : 'hscale', 
  ROLE_DIALOG : 'dialog',
  ROLE_DIRECTORY_PANE : 'gnomeiconlist', 
  ROLE_DOCUMENT_FRAME : 'frame',
  ROLE_DRAWING_AREA : 'drawingarea',
  ROLE_EDITBAR : 'comboboxentry',
  ROLE_EMBEDDED : 'eventbox', 
  ROLE_ENTRY : 'entry', 
  ROLE_EXTENDED : 'custom',
  ROLE_FILE_CHOOSER : 'filechooserdialog',
  ROLE_FILLER : 'default', 
  ROLE_FOCUS_TRAVERSABLE : 'default', 
  ROLE_FONT_CHOOSER : 'fontselectiondialog',
  ROLE_FOOTER : 'label',
  ROLE_FRAME : 'window', 
  ROLE_GLASS_PANE : 'gnomecanvas',
  ROLE_HEADER : 'label',
  ROLE_HEADING : 'label', 
  ROLE_HTML_CONTAINER : 'frame',
  ROLE_ICON : 'gnomeiconentry',
  ROLE_IMAGE : 'image', 
  ROLE_INTERNAL_FRAME : 'frame',
  ROLE_INVALID : 'hseparator',
  ROLE_LABEL : 'label',
  ROLE_LAYERED_PANE : 'drawingarea',
  ROLE_LIST : 'list',
  ROLE_LIST_ITEM : 'listitem', 
  ROLE_MENU : 'menu', 
  ROLE_MENU_BAR : 'menubar',
  ROLE_MENU_ITEM : 'menuitem',
  ROLE_OPTION_PANE : 'frame',
  ROLE_PAGE : 'frame',
  ROLE_PAGE_TAB : 'label', 
  ROLE_PAGE_TAB_LIST : 'notebook',
  ROLE_PANEL : 'frame', 
  ROLE_PARAGRAPH : 'textview',
  ROLE_PASSWORD_TEXT : 'entry', 
  ROLE_POPUP_MENU : 'menu', 
  ROLE_PROGRESS_BAR : 'progressbar',
  ROLE_PUSH_BUTTON : 'button', 
  ROLE_RADIO_BUTTON : 'radiobutton', 
  ROLE_RADIO_MENU_ITEM : 'radiomenuitem',
  ROLE_ROOT_PANE : 'frame',
  ROLE_ROW_HEADER : 'label',
  ROLE_RULER : 'hruler', 
  ROLE_SCROLL_BAR : 'hscrollbar', 
  ROLE_SCROLL_PANE : 'scrolledwindow',
  ROLE_SECTION : '',
  ROLE_SEPARATOR: 'hseparator',
  ROLE_SLIDER : 'hscale', 
  ROLE_SPIN_BUTTON : 'spinbutton', 
  ROLE_SPLIT_PANE : 'hpaned',
  ROLE_STATUS_BAR : 'statusbar',
  ROLE_TABLE : 'table', 
  ROLE_TABLE_CELL : 'toolitem', 
  ROLE_TABLE_COLUMN_HEADER : 'label',
  ROLE_TABLE_ROW_HEADER : 'label',
  ROLE_TEAROFF_MENU_ITEM : 'separatormenuitem',
  ROLE_TERMINAL : 'textview',
  ROLE_TEXT : 'textview',
  ROLE_TOGGLE_BUTTON : 'togglebutton',
  ROLE_TOOL_BAR : 'toolbar', 
  ROLE_TOOL_TIP : 'fixed',
  ROLE_TREE : 'treeview', 
  ROLE_TREE_TABLE : 'treeview',
  ROLE_UNKNOWN : 'custom',
  ROLE_VIEWPORT : 'viewport',
  ROLE_WINDOW : 'window'
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
        fn = os.path.join(GLADE_ICONS_PATH, '%s.png' % name)
        return gtk.gdk.pixbuf_new_from_file(fn)
      except gobject.GError:
        pass
  except Exception, e:
    pass
  fn = os.path.join(ICONS_PATH, 'custom.png')
  return gtk.gdk.pixbuf_new_from_file(fn)
