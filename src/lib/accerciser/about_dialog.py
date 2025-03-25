# -*- coding: utf-8 -*-

'''
Defines the about dialog.

@author: Eitan Isaacson
@organization: Mozilla Foundation
@copyright: Copyright (c) 2006, 2007 Mozilla Foundation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import gi

from gi.repository import Gtk as gtk
from .i18n import _

class AccerciserAboutDialog(gtk.AboutDialog):
  '''
  Creates a dialog with info about the program.

  @cvar APPNAME: Application name.
  @type APPNAME: string
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
  APPNAME = _('Accerciser')
  AUTHORS = ['Eitan Isaacson <eitan@ascender.com>',
             'Peter Parente <pparente@us.ibm.com>',
             'Brian Nitz <brian.nitz@oracle.com>',
             'Javier Hernández <javi@raisingthefloor.org>']
  ARTISTS = ['Eitan Isaacson <eitan@ascender.com>',
             'James Stipp <James_Stipp@us.ibm.com>',
             'Vincent Geddes <vincent.geddes@gmail.com>']
  DOCUMENTERS = ['Eitan Isaacson <eitan@ascender.com>']
  TRANSLATORS = _('translator-credits')
  COMMENTS = _('An interactive Python accessibility explorer')
  COPYRIGHT =  _('accerciser Copyright © 2006, 2007 IBM Corporation (BSD)')
  LICENSE = \
      _('The New BSD License. See the COPYING and NOTICE files for details.')
  WEB_URL = 'http://live.gnome.org/Accerciser'
  WEB_LABEL = _('Web site')
  def __init__(self):
    '''
    Initialize dialog.
    '''
    gtk.AboutDialog.__init__(self)
    self.connect('response', self._onResponse)
    gtk.AboutDialog.set_authors(self, self.AUTHORS)
    gtk.AboutDialog.set_artists(self, self.ARTISTS)
    gtk.AboutDialog.set_documenters(self, self.DOCUMENTERS)
    gtk.AboutDialog.set_comments(self, self.COMMENTS)
    gtk.AboutDialog.set_copyright(self, self.COPYRIGHT)
    gtk.AboutDialog.set_license(self, self.LICENSE)
    gtk.AboutDialog.set_logo_icon_name(self, 'accerciser')
    gtk.AboutDialog.set_program_name(self, self.APPNAME)
#    gtk.AboutDialog.set_version(self, program.get_app_version())
    gtk.AboutDialog.set_website(self, self.WEB_URL)
    gtk.AboutDialog.set_website_label(self, self.WEB_LABEL)

  def _onResponse(self, dialog, response_id):
    '''
    Callback for dialog responses, always destroy it.

    @param dialog: This dialog.
    @type dialog: L{AccerciserAboutDialog}
    @param response_id: Response ID recieved.
    @type response_id: integer
    '''
    self.destroy()

