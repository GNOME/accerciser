# -*- coding: utf-8 -*-
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

from gi.repository import Gtk, GObject
#from gnome import program_get, url_show

_ = lambda x: x
#Gtk.about_dialog_set_url_hook(lambda dialog, url, data: url_show(url), None)


class MacaroonAboutDialog(Gtk.AboutDialog):
  '''
  Creates a dialog with info about the program.

  @cvar AUTHORS: List of authors.
  @type AUTHORS: list of string
  @cvar ARTISTS: List of artists.
  @type ARTISTS:list of string
  @cvar DOCUMENTERS: List of documenters.
  @type DOCUMENTERS: list of string
  @cvar TRANSLATORS: Translator.
  @type TRANSLATORS: string
  @cvar COMMENTS: Comments about program.
  @type COMMENTS: string
  @cvar COPYRIGHT: Copyright notice.
  @type COPYRIGHT: string
  @cvar LICENSE: License of program.
  @type LICENSE: string
  @cvar WEB_URL: URL to program's website.
  @type WEB_URL: string
  @cvar WEB_LABEL: Label of URL button.
  @type WEB_LABEL: string
  '''
  AUTHORS = ['Eitan Isaacson <eitan@ascender.com>']
  ARTISTS = []
  DOCUMENTERS = []
  TRANSLATORS = _('translator-credits')
  COMMENTS = _('A desktop macro tool')
  COPYRIGHT =  _('macaroon Copyright © 2007 Eitan Isaacson')
  LICENSE = ''
  WEB_URL = 'http://live.gnome.org/Macaroon'
  WEB_LABEL = _('Web site')
  def __init__(self):
    '''
    Initialize dialog.
    '''
#    program = program_get()
    GObject.GObject.__init__(self)
    self.connect('response', self._onResponse)
    Gtk.AboutDialog.set_authors(self, self.AUTHORS)
    Gtk.AboutDialog.set_artists(self, self.ARTISTS)
    Gtk.AboutDialog.set_documenters(self, self.DOCUMENTERS)
    Gtk.AboutDialog.set_comments(self, self.COMMENTS)
    Gtk.AboutDialog.set_copyright(self, self.COPYRIGHT)
    Gtk.AboutDialog.set_license(self, self.LICENSE)
    Gtk.AboutDialog.set_logo_icon_name(self, 'macaroon')
#    Gtk.AboutDialog.set_version(self, program.get_app_version())
    Gtk.AboutDialog.set_website(self, self.WEB_URL)
    Gtk.AboutDialog.set_website_label(self, self.WEB_LABEL)

  def _onResponse(self, dialog, response_id):
    '''
    Callback for dialog responses, always destroy it.

    @param dialog: This dialog.
    @type dialog: L{MacaroonAboutDialog}
    @param response_id: Response ID recieved.
    @type response_id: integer
    '''
    self.destroy()
