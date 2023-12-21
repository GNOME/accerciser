'''
Defines the menus used in the application.

@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

from gi.repository import Gio as gio

from .i18n import _

main_menu = gio.Menu()
file_menu = gio.Menu()
main_menu.append_submenu(_('_File'), file_menu)
edit_menu = gio.Menu()
main_menu.append_submenu(_('_Edit'), edit_menu)
bookmarks_menu = gio.Menu()
bookmarks_menu_general_section = gio.Menu()
bookmarks_menu.append_section(None, bookmarks_menu_general_section)
bookmarks_menu_individual_section = gio.Menu()
bookmarks_menu.append_section(None, bookmarks_menu_individual_section)
main_menu.append_submenu(_('_Bookmarks'), bookmarks_menu)
view_menu = gio.Menu()
main_menu.append_submenu(_('_View'), view_menu)
view_menu_general_section = gio.Menu()
view_menu.append_section(None, view_menu_general_section)
view_menu_treeview_section = gio.Menu()
view_menu.append_section(None, view_menu_treeview_section)
help_menu = gio.Menu()
main_menu.append_submenu(_('_Help'), help_menu)

treeview_context_menu = gio.Menu()
