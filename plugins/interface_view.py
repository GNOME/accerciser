'''
AT-SPI interface viewer plugin.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import pyLinAcc
import gtk
import os.path
import pango
from accerciser.plugin import ViewportPlugin
from accerciser.icons import getIcon
from accerciser.i18n import _, N_

GLADE_FILE = os.path.join(os.path.dirname(__file__), 
                          'interface_view.glade')

class InterfaceViewer(ViewportPlugin):
  plugin_name = N_('Interface Viewer')
  plugin_name_localized = _(plugin_name)
  plugin_description = N_('Allows viewing of various interface properties')
  def init(self):
    self.main_xml = gtk.glade.XML(GLADE_FILE, 'iface_view_frame')
    frame = self.main_xml.get_widget('iface_view_frame')
    self.plugin_area.add(frame)
    self.main_xml.signal_autoconnect(self)

  def close(self):
    pass

