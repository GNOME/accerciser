'''
Defines the preferences dialog.

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
from gi.repository import Gdk as gdk
from gi.repository import Atk as atk
from gi.repository.Gio import Settings as GSettings

from .i18n import _
from . import node
from .tools import parseColorString

class AccerciserPreferencesDialog(gtk.Dialog):
  '''
  Class that creates a preferences dialog.
  '''
  def __init__(self, plugins_view=None, hotkeys_view=None):
    '''
    Initialize a preferences dialog.

    @param plugins_view: Treeview of plugins.
    @type plugins_view: L{PluginManager._View}
    @param hotkeys_view: Treeview of global hotkeys.
    @type hotkeys_view: L{HotkeyTreeView}
    '''
    gtk.Dialog.__init__(self, title=_('accerciser Preferences'))
    close_button = self.add_button(_('_Close'), gtk.ResponseType.CLOSE)
    close_button.set_image(gtk.Image.new_from_icon_name('window-close', gtk.IconSize.BUTTON))
    self.connect('response', self._onResponse)
    self.set_default_size(500, 250)
    notebook = gtk.Notebook()
    vbox = self.get_children()[0]
    vbox.pack_start(notebook, True, True, 2)
    for view, section in [(plugins_view, _('Plugins')),
                          (hotkeys_view, _('Global Hotkeys'))]:
      if view is not None:
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.ShadowType.IN)
        sw.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        sw.set_size_request(500, 150)
        sw.add(view)
        notebook.append_page(sw, gtk.Label.new(section))

    notebook.append_page(_HighlighterView(), gtk.Label.new(_('Highlighting')))

  def _onResponse(self, dialog, response_id):
    '''
    Callback for dialog responses, always destroy it.

    @param dialog: This dialog.
    @type dialog: L{AccerciserPreferencesDialog}
    @param response_id: Response ID recieved.
    @type response_id: integer
    '''
    dialog.destroy()

class _HighlighterView(gtk.Grid):
  '''
  A container widget with the settings for the highlighter.
  '''
  def __init__(self):
    gtk.Grid.__init__(self)
    self.set_margin_top(12)
    self.set_margin_bottom(12)
    self.set_margin_start(18)
    self.set_margin_end(12)
    self.set_column_spacing(6)
    self.gsettings = GSettings.new('org.a11y.Accerciser')
    self._buildUI()

  def _buildUI(self):
    '''
    Programatically build the UI.
    '''
    labels = [None, None, None]
    controls = [None, None, None]
    labels[0] = gtk.Label.new(_('Highlight duration:'))
    controls[0] = gtk.SpinButton()
    controls[0].set_range(0.01, 5)
    controls[0].set_digits(2)
    controls[0].set_value(self.gsettings.get_double('highlight-duration'))
    controls[0].set_increments(0.01, 0.1)
    controls[0].connect('value-changed', self._onDurationChanged)
    labels[1] = gtk.Label.new(_('Border color:'))
    controls[1] = self._ColorButton(node.BORDER_COLOR, node.BORDER_ALPHA)
    controls[1].connect('color-set', self._onColorSet, 'highlight-border')
    controls[1].set_tooltip_text(_('The border color of the highlight box'))
    labels[2] = gtk.Label.new(_('Fill color:'))
    controls[2] = self._ColorButton(node.FILL_COLOR, node.FILL_ALPHA)
    controls[2].connect('color-set', self._onColorSet, 'highlight-fill')
    controls[2].set_tooltip_text(_('The fill color of the highlight box'))

    for label, control, row in zip(labels, controls, range(3)):
      label.set_alignment(0, 0.5)
      self.attach(label, 0, row, 1, 1)
      self.attach(control, 1, row, 1, 1)

    for label, control in zip([x.get_accessible() for x in labels],
                              [x.get_accessible() for x in controls]):
      label.add_relationship(atk.RelationType.LABEL_FOR, control)
      control.add_relationship(atk.RelationType.LABELLED_BY, label)

  def _onDurationChanged(self, spin_button):
    '''
    Callback for the duration spin button. Update key and the global variable
    in the L{node} module.

    @param spin_button: The spin button that emitted the value-changed signal.
    @type spin_button: gtk.SpinButton
    '''
    node.HL_DURATION = int(spin_button.get_value()*1000)
    self.gsettings.set_double('highlight-duration',
                            spin_button.get_value())


  def _onColorSet(self, color_button, key):
    '''
    Callback for a color button. Update gsettings and the global variables
    in the L{node} module.

    @param color_button: The color button that emitted the color-set signal.
    @type color_button: l{_HighlighterView._ColorButton}
    @param key: the key name suffix for this color setting.
    @type key: string
    '''
    if 'fill' in key:
      node.FILL_COLOR = color_button.get_rgb_string()
      node.FILL_ALPHA = color_button.get_alpha_float()
    else:
      node.BORDER_COLOR = color_button.get_rgb_string()
      node.BORDER_ALPHA = color_button.get_alpha_float()

    self.gsettings.set_string(key, color_button.get_rgba_string())

  class _ColorButton(gtk.ColorButton):
    '''
    ColorButton derivative with useful methods for us.
    '''
    def __init__(self, color, alpha):
      color = gdk.color_parse(color)
      gtk.ColorButton.__init__(self)
      self.set_use_alpha(True)
      self.set_alpha(int(alpha*0xffff))
      self.set_color(color)

    def get_rgba_string(self):
      '''
      Get the current color and alpha in string format.

      @return: String in the format of #rrggbbaa.
      @rtype: string.
      '''
      color = self.get_color()
      color_val = 0
      color_val |= color.red >> 8 << 24
      color_val |= color.green >> 8 << 16
      color_val |= color.blue >> 8 << 8
      color_val |= self.get_alpha() >> 8
      return \
          '#' + hex(color_val).replace('0x', '').replace('L', '').rjust(8, '0')

    def get_rgb_string(self):
      '''
      Get the current color in string format.

      @return: String in the format of #rrggbb.
      @rtype: string.
      '''
      color = self.get_color()
      color_val = 0
      color_val |= color.red >> 8 << 16
      color_val |= color.green >> 8 << 8
      color_val |= color.blue >> 8
      return \
          '#' + hex(color_val).replace('0x', '').replace('L', '').rjust(6, '0')

    def get_alpha_float(self):
      '''
      Get the current alpha as a value from 0.0 to 1.0.
      '''
      return self.get_alpha()/float(0xffff)
