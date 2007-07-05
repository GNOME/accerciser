'''
AT-SPI interface viewer plugin.

@author: Eitan Isaacson
@organization: Mozilla Foundation
@copyright: Copyright (c) 2007 Mozilla Foundation
@license: BSD

All rights reserved. This program and the accompanying materials are made 
available under the terms of the BSD which accompanies this distribution, and 
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import pyatspi
import gtk
import os.path
import pango
from accerciser.plugin import ViewportPlugin
from accerciser.icons import getIcon
from accerciser.i18n import _, N_

GLADE_FILE = os.path.join(os.path.dirname(__file__), 
                          'interface_view.glade')

class InterfaceViewer(ViewportPlugin):
  '''
  Interface Viewer plugin class.

  @ivar label_role: Top plugin label that displays the role name and 
  the accessible name.
  @type label_role: gtk.Label
  @ivar sections: List of L{_InterfaceSection} instances.
  @type sections: list  
  '''
  plugin_name = N_('Interface Viewer')
  plugin_name_localized = _(plugin_name)
  plugin_description = N_('Allows viewing of various interface properties')

  def init(self):
    '''
    Intialize plugin.
    '''
    glade_xml = gtk.glade.XML(GLADE_FILE, 'iface_view_frame')
    frame = glade_xml.get_widget('iface_view_frame')
    self.label_role = glade_xml.get_widget('label_role')
    self.plugin_area.add(frame)
    self.sections = [
      _SectionAccessible(glade_xml, self.node),
      _SectionAction(glade_xml, self.node),
      _SectionApplication(glade_xml, self.node),
      _SectionComponent(glade_xml, self.node),
      _SectionDocument(glade_xml, self.node),
      _SectionHyperlink(glade_xml, self.node),
      _SectionHypertext(glade_xml, self.node),
      _SectionImage(glade_xml, self.node),
      _SectionSelection(glade_xml, self.node),
      _SectionStreamableContent(glade_xml, self.node),
      _SectionTable(glade_xml, self.node),
      _SectionText(glade_xml, self.node),
      _SectionValue(glade_xml, self.node)]

    # Mark all expanders with no associated section classes as unimplemented
    implemented_sections = [obj.interface_name.lower() for obj in self.sections]
    vbox_ifaces = glade_xml.get_widget('vbox_ifaces')
    for expander in vbox_ifaces.get_children():
      expander.connect('focus-in-event', self._onScrollToFocus)
      iface_name = expander.name.replace('expander_', '')
      if iface_name not in implemented_sections:
        section = _InterfaceSection(glade_xml, self.node, iface_name)
        section.disable()

  def onAccChanged(self, acc):
    '''
    Method that is invoked when the main accessible selection s changed.

    @param acc: New accessible
    @type acc: Accessibility.Accessible
    '''
    role = acc.getRoleName()
    name = acc.name
    if name:
      role_name = '%s: %s' % (role, name)
    else:
      role_name = role
    self.label_role.set_markup('<b>%s</b>' % role_name)
    interfaces = pyatspi.listInterfaces(acc)
    for section_obj in self.sections:
      section_obj.disable()
      if section_obj.interface_name in interfaces:
        section_obj.enable(acc)

  def _onScrollToFocus(self, widget, event):
    '''
    Scrolls a focused expander in plugin area into view.
    
    @param widget: Widget that has the focus
    @type widget: gtk.Widget
    @param event: Event object.
    @type direction: gtk.gdk.Event
    '''
    x, y = widget.translate_coordinates(self.viewport, 0, 0)
    w, h = widget.size_request()
    vw, vh = self.allocation.width, self.allocation.height

    adj = self.viewport.get_vadjustment()
    if y+h > vh:
      adj.value += min((y+h) - vh + 7, y)
    elif y < 0:
      adj.value = max(adj.value + y, adj.lower)

class _InterfaceSection(object):
  '''
  An abstract class that defines the interface for interface sections.

  @cvar interface_name: Name of interface this section is for.
  @type interface_name: string
  
  @ivar node: Application-wide L{Node}.
  @type node: L{Node}
  @ivar expander: The section expander widget.
  @type expander: gtk.Expander
  @ivar event_listeners: List of client and event pairs that are 
  registered by this section. They are typically registered an population time,
  and alwas deregistered on L{clearUI}.
  @type event_listeners: list
  '''
  interface_name = None
  def __init__(self, glade_xml, node, interface_name=None):
    '''
    Initialize section object. and call init() for derived classes.
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    @param node: Application-wide node of selected accessible.
    @type node: L{Node}
    @param interface_name: Override default interface name.
    @type interface_name: string
    '''
    self.interface_name = interface_name or self.interface_name
    self.node = node
    self.expander = \
        glade_xml.get_widget('expander_%s' % self.interface_name.lower())
    self._setExpanderChildrenSensitive(False)
    self.event_listeners = []
    self.init(glade_xml)

  def init(self, glade_xml):
    '''
    Abtract method for initializing section-specific code.
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    pass

  def enable(self, acc):
    '''
    Make section sensitive and populate it.
    
    @param acc: Accessible to use for information when populating section.
    @type acc: Accessibility.Accessible
    '''
    self._setExpanderChildrenSensitive(True)
    self.populateUI(acc)

  def populateUI(self, acc):
    '''
    Abstract method for section specific populating code.
    
    @param acc: Accessible to use for information when populating section.
    @type acc: Accessibility.Accessible
    '''
    pass

  def disable(self):
    '''
    Disable section, make insensitive.
    '''
    self._setExpanderChildrenSensitive(False)
    for client, event_names in self.event_listeners:
      pyatspi.Registry.deregisterEventListener(client, *event_names)
    self.clearUI()

  def clearUI(self):
    '''
    Abstract method for section-specific cleanup.
    '''
    pass

  def _setExpanderChildrenSensitive(self, sensitive, expander=None):
    '''
    Convinience method for making the expander's children insensitive.
    We don't want tomake the expander itself insensitive because the user might
    still want to keep it open or close it when it is disabled.
    
    @param sensitive: True for sensitive.
    @type sensitive: boolean
    @param expander: Expander widget. Uses instance's expander by default.
    @type expander: gtk.Expander
    '''
    expander = expander or self.expander
    label = expander.get_label_widget()
    label_text = label.get_label()
    if sensitive:
      label_text = label_text.replace(_(' (not implemented)'), '')
    elif _(' (not implemented)') not in label_text:
      label_text += _(' (not implemented)')
    label.set_label(label_text)
    for child in expander.get_children():
      child.set_sensitive(sensitive)

  def _isSelectedInView(self, selection):
    '''
    Convinience method for determining if a given treeview selection has any 
    selected nodes.
    
    @param selection: Selection to check.
    @type selection: gtk.TreeSelection
    
    @return: True is something is selected
    @rtype: boolean
    '''
    model, rows = selection.get_selected_rows()
    something_is_selected = bool(rows)
    return something_is_selected

  def _onViewSelectionChanged(self, selection, *widgets):
    '''
    Convinience callback for selection changes. Useful for setting given 
    widgets to be sensitive only when something is selected, for example 
    action buttons. 
    
    @param selection: The selection object that triggered the callback.
    @type selection: gtk.TreeSelection
    @param widgets: list of widgets that should be made sensitive/insensitive 
    on selection changes.
    @type widgets: list of gtk.Widget
    '''
    for widget in widgets:
      widget.set_sensitive(self._isSelectedInView(selection))
      
  def registerEventListener(self, client, *event_names):
    pyatspi.Registry.registerEventListener(client, *event_names)
    self.event_listeners.append((client, event_names))

class _SectionAccessible(_InterfaceSection):
  '''
  A class that populates an Accessible interface section.

  @ivar states_model: Model for accessible states.
  @type states_model: gtk.ListStore
  @ivar relations_view: Tree view for accessible relations.
  @type relations_view: gtk.TreeView
  @ivar relations_model: Model for accessible relations.
  @type relations_view: gtk.TreeStore
  @ivar header_bg: Background color for relation header.
  @type header_bg: gtk.gdk.Color
  @ivar relation_bg: Background color for relation row.
  @type relation_bg: gtk.gdk.Color
  @ivar attr_model: Model for accessible attributes.
  @type attr_model: gtk.ListStore
  '''

  interface_name = 'Accessible'

  def init(self, glade_xml):
    '''
    Initialization that is specific to the Accessible interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    glade_xml.signal_autoconnect(self)
    # Child count and description labels
    self.child_count_label = glade_xml.get_widget('label_acc_child count')
    self.desc_label = glade_xml.get_widget('label_acc_desc')

    # configure states tree view
    treeview = glade_xml.get_widget('states_view')
    self.states_model = gtk.ListStore(str)
    treeview.set_model(self.states_model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=0)
    treeview.append_column(tvc)

    # configure relations tree view
    self.relations_view = glade_xml.get_widget('relations_view')
    self.relations_model = gtk.TreeStore(gtk.gdk.Pixbuf, str, object)
    self.relations_view.set_model(self.relations_model)
    crt = gtk.CellRendererText()
    crp = gtk.CellRendererPixbuf()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crp, False)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crp, pixbuf=0)
    tvc.set_attributes(crt, text=1)
    tvc.set_cell_data_func(crt, self._relationCellDataFunc)
    tvc.set_cell_data_func(crp, self._relationCellDataFunc)
    self.relations_view.append_column(tvc)
    # preset the different bg colors
    style = gtk.Style ()
    self.header_bg = style.bg[gtk.STATE_NORMAL]
    self.relation_bg = style.base[gtk.STATE_NORMAL]
    selection = self.relations_view.get_selection()
    selection.set_select_function(self._relationSelectFunc)
    show_button = glade_xml.get_widget('button_relation_show')
    show_button.set_sensitive(self._isSelectedInView(selection))
    selection.connect('changed', self._onViewSelectionChanged, show_button)

    # configure accessible attributes tree view
    treeview = glade_xml.get_widget('accattrib_view')
    self.attr_model = gtk.ListStore(str, str)
    treeview.set_model(self.attr_model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=0)
    treeview.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=1)
    treeview.append_column(tvc)

  def populateUI(self, acc):
    '''
    Populate the Accessible section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''

    self.child_count_label.set_text(str(acc.childCount))
    self.desc_label.set_label(acc.description or _('<i>(no description)</i>'))

    states = [pyatspi.stateToString(s) for s in acc.getState().getStates()]
    states.sort()
    map(self.states_model.append, [[state] for state in states])
    
    try:
      attribs = acc.getAttributes()
    except:
      pass
    else:
      for attr in attribs:
        name, value = attr.split(':', 1)
        self.attr_model.append([name, value])

    relations = acc.getRelationSet()
    for relation in relations:
      r_type_name = repr(relation.getRelationType()).replace('RELATION_', '')
      r_type_name = r_type_name.replace('_', ' ').lower().capitalize()
      iter = self.relations_model.append(None, [None, r_type_name, None])
      for i in range(relation.getNTargets()):
        acc = relation.getTarget(0)
        self.relations_model.append(iter, [getIcon(acc), acc.name, acc])
    self.relations_view.expand_all()

    self.registerEventListener(self._accEventState, 'object:state-changed')

  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.relations_model.clear()
    self.states_model.clear()
    self.attr_model.clear()

  def _relationCellDataFunc(self, tvc, cellrenderer, model, iter):
    '''
    Make relation-type headers distinguishable by tweaking the visible styling.
    
    @param tvc: The given tree view column
    @type tvc: gtk.TreeViewColumn
    @param cellrenderer: The given cell renderer.
    @type cellrenderer: gtk.CellRenderer
    @param model: The relations data model.
    @type model: gtk.TreeStore
    @param iter: The current iter.
    @type iter: gtk.TreeIter
    '''
    if len(model.get_path(iter)) == 1:
      cellrenderer.set_property('cell-background-gdk', self.header_bg)
      cellrenderer.set_property('mode', gtk.CELL_RENDERER_MODE_INERT)
      if isinstance(cellrenderer, gtk.CellRendererText):
        cellrenderer.set_property('style', pango.STYLE_ITALIC)
      elif isinstance(cellrenderer, gtk.CellRendererPixbuf):
        cellrenderer.set_property('visible', False)
    else:
      cellrenderer.set_property('cell-background-gdk', self.relation_bg)
      cellrenderer.set_property('mode', gtk.CELL_RENDERER_MODE_ACTIVATABLE)
      if isinstance(cellrenderer, gtk.CellRendererText):
        cellrenderer.set_property('style', pango.STYLE_NORMAL)
      elif isinstance(cellrenderer, gtk.CellRendererPixbuf):
        cellrenderer.set_property('visible', True)

  def _relationSelectFunc(self, path):
    '''
    Make relation-type headers unselectable.
    
    @param path: The path about to be selected
    @type path: tuple
    
    @return: True if selectable
    @rtype: boolean
    '''
    return not len(path) == 1

  def _onRelationShow(self, relations_view, *more_args):
    '''
    Callback for row activation or button press. Selects the related
    accessible in the main application.
    
    @param relations_view: The relations treeview.
    @type relations_view: gtk.TreeView
    @param *more_args: More arguments that are provided by variuos types of
    signals, but we discard them all.
    @type *more_args: list
    '''
    selection = relations_view.get_selection()
    model, iter = selection.get_selected()
    if iter:
      acc = model[iter][2]
      if acc:
        self.node.update(acc)
  
  def _accEventState(self, event):
    '''
    Callback for accessible state changes. Repopulates the states model.
    
    @param event: Event that triggered this callback.
    @type event: Accessibility.Event
    '''
    if self.node.acc == event.source:
      self.states_model.clear()
      states = [pyatspi.stateToString(s) for s in \
                  self.node.acc.getState().getStates()]
      states.sort()
      map(self.states_model.append, [[state] for state in states])        


class _SectionAction(_InterfaceSection):
  '''
  A class that populates an Action interface section.

  @ivar actions_model: Model for accessible states.
  @type actions_model: gtk.ListStore
  @ivar action_selection: Current selection of actions tree view.
  @type action_selection: gtk.TreeSelection  
  '''
  interface_name = 'Action'
  def init(self, glade_xml):
    '''
    Initialization that is specific to the Action interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    glade_xml.signal_autoconnect(self)    
    # configure actions tree view
    treeview = glade_xml.get_widget('treeview_action')
    self.actions_model = gtk.ListStore(int, str, str, str)
    treeview.set_model(self.actions_model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Name'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=1)
    treeview.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Description'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=2)
    treeview.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Key binding'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=3)
    treeview.append_column(tvc)
    self.action_selection = treeview.get_selection()
    show_button = glade_xml.get_widget('button_action_do')
    show_button.set_sensitive(self._isSelectedInView(self.action_selection))
    self.action_selection.connect('changed', 
                                  self._onViewSelectionChanged, show_button)

  def populateUI(self, acc):
    '''
    Populate the Action section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    ai = acc.queryAction()
    for i in range(ai.nActions):
      self.actions_model.append([i, ai.getName(i),
                                 ai.getDescription(i),
                                 ai.getKeyBinding(i)])

  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.actions_model.clear()

  def _onActionRowActivated(self, treeview, path, view_column):
    '''
    Callback for row activation in action treeview. Performs actions.
    
    @param treeview: Actions tree view.
    @type treeview: gtk.TreeView
    @param path: Path of activated role.
    @type path: tuple
    @param view_column: The column that was clicked
    @type view_column: integer
    '''
    action_num = self.actions_model[path][0]
    ai = self.node.acc.queryAction()
    ai.doAction(action_num)

  def _onActionClicked(self, button):
    '''
    Callback for "do action" button. Performs action of currently selected row.
    
    @param button: The button that was pressed.
    @type button: gtk.Button
    '''
    actions_model, iter = self.action_selection.get_selected()
    action_num = actions_model[iter][0]
    ai = self.node.acc.queryAction()
    ai.doAction(action_num)

class _SectionApplication(_InterfaceSection):
  '''
  A class that populates an Application interface section.
  
  @ivar label_id: Label that displays application id info.
  @type label_id: gtk.Label
  @ivar label_tk: Label for toolkit name.
  @type label_tk: gtk.Label
  @ivar label_version: Label for toolkit version.
  @type label_version: gtk.Label
  '''
  interface_name = 'Application'
  def init(self, glade_xml):
    '''
    Initialization that is specific to the Application interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    self.label_id = glade_xml.get_widget('label_app_id')
    self.label_tk = glade_xml.get_widget('label_app_tk')
    self.label_version = glade_xml.get_widget('label_app_version')
  
  def populateUI(self, acc):
    '''
    Populate the Application section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    ai = acc.queryApplication()
    self.label_id.set_text(repr(ai.id))
    self.label_tk.set_text(ai.toolkitName)
    self.label_version.set_text(ai.version)

  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.label_id.set_text('')
    self.label_tk.set_text('')
    self.label_version.set_text('')

class _SectionComponent(_InterfaceSection):
  '''
  A class that populates a Component interface section.
  
  @ivar label_posrel: Relative position label
  @type label_posrel: gtk.Label
  @ivar label_posabs: Absolute position label
  @type label_posabs: gtk.Label
  @ivar label_layer: Layer label
  @type label_layer: gtk.Label
  @ivar label_zorder: Z-order label
  @type label_zorder: gtk.Label
  @ivar label_alpha: Alpha label
  @type label_alpha: gtk.Label
  '''
  interface_name = 'Component'
  def init(self, glade_xml):
    '''
    Initialization that is specific to the Component interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    self.label_posrel = glade_xml.get_widget('absolute_position_label')
    self.label_posabs = glade_xml.get_widget('relative_position_label')
    self.label_size = glade_xml.get_widget('size_label')
    self.label_layer = glade_xml.get_widget('layer_label')
    self.label_zorder = glade_xml.get_widget('zorder_label')
    self.label_alpha = glade_xml.get_widget('alpha_label')

  def populateUI(self, acc):
    '''
    Populate the Component section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    ci = acc.queryComponent()
    bbox = ci.getExtents(pyatspi.DESKTOP_COORDS)
    self.label_posabs.set_text('%d, %d' % (bbox.x, bbox.y))
    self.label_size.set_text('%dx%d' % (bbox.width, bbox.height))
    bbox = ci.getExtents(pyatspi.WINDOW_COORDS)
    self.label_posrel.set_text('%d, %d' % (bbox.x, bbox.y))
    layer = ci.getLayer()
    self.label_layer.set_text(repr(ci.getLayer()).replace('LAYER_',''))
    self.label_zorder.set_text(repr(ci.getMDIZOrder()))
    self.label_alpha.set_text(repr(ci.getAlpha()))
    self.registerEventListener(self._accEventComponent, 
                               'object:bounds-changed',
                               'object:visible-data-changed')
  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.label_posrel.set_text('')
    self.label_posabs.set_text('')
    self.label_size.set_text('')
    self.label_layer.set_text('')
    self.label_zorder.set_text('')
    self.label_alpha.set_text('')

  def _accEventComponent(self, event):
    '''
    Callback for whenever any of the component attributes change.
    
    @param event: Evnt that triggered this callback.
    @type event: Accessibility.Event
    '''
    if event.source == self.node.acc:
      self.populateUI(event.source)

class _SectionDocument(_InterfaceSection):
  interface_name = 'Document'
  '''
  A class that populates an Component interface section.

  @ivar attr_model: Attribute data model
  @type attr_model: gtk.ListStore
  @ivar label_locale: Locale label
  @type label_locale: gtk.Label
  '''

  def init(self, glade_xml):
    '''
    Initialization that is specific to the Document interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    # configure document attributes tree view
    treeview = glade_xml.get_widget('docattrib_view')
    self.attr_model = gtk.ListStore(str, str)
    treeview.set_model(self.attr_model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=0)
    treeview.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=1)
    treeview.append_column(tvc)
    self.label_locale = glade_xml.get_widget('label_doc_locale')

  def populateUI(self, acc):
    '''
    Populate the Document section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    di = acc.queryDocument()

    self.label_locale.set_text(di.getLocale())

    try:
      attribs = di.getAttributes()
    except:
      attribs = None
    if attribs:
      for attr in attribs:
        name, value = attr.split(':', 1)
        self.attr_model.append([name, value])

  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.attr_model.clear()
    self.label_locale.set_text('')

class _SectionHyperlink(_InterfaceSection):
  interface_name = 'Hyperlink'
  '''
  A placeholder class for Hyperlink interface section.
  '''

class _SectionHypertext(_InterfaceSection):
  '''
  A class that populates an Hypertext interface section.
  
  @ivar links_model: Data model for available links.
  @type links_model: gtk.ListStore
  '''
  interface_name = 'Hypertext'
  def init(self, glade_xml):
    '''
    Initialization that is specific to the Hypertext interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    glade_xml.signal_autoconnect(self)
    # configure links tree view
    treeview = glade_xml.get_widget('treeview_links')
    # It's a treestore because of potential multiple anchors
    self.links_model = gtk.TreeStore(int, # Link index
                          str, # Name
                          str, # Description
                          str, # URI
                          int, # Start offset
                          int, # End offset
                          object) # Anchor object
    treeview.set_model(self.links_model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Name'))
    tvc.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
    tvc.set_resizable(True)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=1)
    treeview.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('URI'))
    tvc.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
    tvc.set_resizable(True)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=3)
    treeview.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Start'))
    tvc.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
    tvc.set_resizable(True)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=4)
    treeview.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('End'))
    tvc.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
    tvc.set_resizable(True)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=5)
    treeview.append_column(tvc)    
    selection = treeview.get_selection()
    show_button = glade_xml.get_widget('button_hypertext_show')
    show_button.set_sensitive(self._isSelectedInView(selection))
    selection.connect('changed', self._onViewSelectionChanged, show_button)


  def populateUI(self, acc):
    '''
    Populate the Hypertext section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    hti = acc.queryHypertext()

    for link_index in xrange(hti.getNLinks()):
      link = hti.getLink(link_index)
      iter = self.links_model.append(None,
                                     [link_index, 
                                      '', '', '',
                                      link.startIndex, 
                                      link.endIndex, None])
      for anchor_index in xrange(link.nAnchors):
        acc_obj = link.getObject(anchor_index)
        self.links_model.append(iter,
                                [link_index, acc_obj.name, acc_obj.description,
                                 link.getURI(anchor_index), 
                                 link.startIndex, link.endIndex, acc_obj])
        if anchor_index == 0:
          self.links_model[iter][1] = \
              acc_obj.name # Otherwise the link is nameless.


  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.links_model.clear()

  def _onLinkShow(self, link_view, *more_args):
    '''
    Callback for row activation or button press. Selects the related
    link accessible in the main application.
    
    @param link_view: The links tree view.
    @type link_view: gtk.TreeView
    @param *more_args: More arguments that are provided by variuos types of
    signals, but we discard them all.
    @type *more_args: list
    '''
    selection = link_view.get_selection()
    model, iter = selection.get_selected()
    if iter:
      acc = model[iter][6]
      if acc:
        self.node.update(acc)


class _SectionImage(_InterfaceSection):
  '''
  A class that populates an Image interface section.
  
  @ivar label_pos: Position label
  @type label_pos: gtk.Label
  @ivar label_size: Size label
  @type label_size: gtk.Label
  '''
  interface_name = 'Image'

  def init(self, glade_xml):
    '''
    Initialization that is specific to the Image interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    self.label_pos = glade_xml.get_widget('img_position_label')
    self.label_size = glade_xml.get_widget('img_size_label')
    self.label_locale = glade_xml.get_widget('img_locale_label')
    self.label_desc = glade_xml.get_widget('img_locale_label')

  def populateUI(self, acc):
    '''
    Populate the Image section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    ii = acc.queryImage()

    bbox = ii.getImageExtents(pyatspi.DESKTOP_COORDS)
    self.label_pos.set_text('%d, %d' % (bbox.x, bbox.y))
    self.label_size.set_text('%dx%d' % (bbox.width, bbox.height))
    self.label_desc.set_label(ii.imageDescription or \
                                _('<i>(no description)</i>'))
    self.label_locale.set_text(ii.imageLocale)
  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.label_pos.set_text('')
    self.label_size.set_text('')

class _SectionSelection(_InterfaceSection):
  '''
  A class that populates a Selection interface section.

  @ivar sel_model: Data model for child selection options.
  @type sel_model: gtk.ListStore
  @ivar sel_selection: Selection in selection treeview.
  @type sel_selection: gtk.TreeSelection
  @ivar button_select_all: Button for selecting all of the selection nodes.
  @type button_select_all: gtk.Button
  '''
  interface_name = 'Selection'

  def init(self, glade_xml):
    '''
    Initialization that is specific to the Selection interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    glade_xml.signal_autoconnect(self)
    # configure selection tree view
    treeview = glade_xml.get_widget('treeview_selection')
    self.sel_model = gtk.ListStore(gtk.gdk.Pixbuf, str, object)
    treeview.set_model(self.sel_model)
    crt = gtk.CellRendererText()
    crp = gtk.CellRendererPixbuf()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crp, False)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crp, pixbuf=0)
    tvc.set_attributes(crt, text=1)
    treeview.append_column(tvc)
    # connect selection changed signal
    self.sel_selection = treeview.get_selection()
    show_button = glade_xml.get_widget('button_select_clear')
    show_button.set_sensitive(self._isSelectedInView(self.sel_selection))
    self.sel_selection.connect('changed', 
                               self._onViewSelectionChanged, 
                               show_button)
    self.sel_selection.connect('changed', 
                               self._onSelectionSelected)
    self.button_select_all = glade_xml.get_widget('button_select_all')

  def populateUI(self, acc):
    '''
    Populate the Selection section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    if acc.childCount > 50:
      theme = gtk.icon_theme_get_default()
      self.sel_model.append(
        [theme.load_icon('gtk-dialog-warning', 24, 
                         gtk.ICON_LOOKUP_USE_BUILTIN),
         _('Too many selectable children'), None])
      # Set section as insensitive, but leave expander label sensitive.
      section_widgets = self.expander.get_children()
      section_widgets.remove(self.expander.get_label_widget())
      for child in section_widgets:
        child.set_sensitive(False)
      return

    for child in acc:
      if child is not None:
        state = child.getState()
        if state.contains(pyatspi.STATE_SELECTABLE):
          self.sel_model.append([getIcon(child),child.name, child])
    
    state = acc.getState()
    multiple_selections = state.contains(pyatspi.STATE_MULTISELECTABLE)

    self.button_select_all.set_sensitive(multiple_selections)

    if multiple_selections:
      self.sel_selection.set_mode = gtk.SELECTION_MULTIPLE
    else:
      self.sel_selection.set_mode = gtk.SELECTION_SINGLE

  def _onSelectionSelected(self, selection):
    '''
    Callback for selection change in the selection treeview. Confusing?
    
    @param selection: The treeview's selection object.
    @type selection: gtk.TreeSelection
    '''
    try:
      si = self.node.acc.querySelection()
    except NotImplementedError:
      return

    model, paths = selection.get_selected_rows()
    selected_children = [path[0] for path in paths]
    
    for child_index in range(len(self.node.acc)):
      if child_index in selected_children:
        si.selectChild(child_index)
      else:
        si.deselectChild(child_index)

  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.sel_model.clear()
  
  def _onSelectionClear(self, widget):
    '''
    Callback for selection clear button.
    
    @param widget: Widget that triggered callback.
    @type widget: gtk.Widget
    '''
    si = self.node.acc.querySelection()

    self.sel_selection.unselect_all()
    si.clearSelection()

  def _onSelectAll(self, widget):
    '''
    Callback for selection select all button.
    
    @param widget: Widget that triggered callback.
    @type widget: gtk.Widget
    '''
    si = self.node.acc.querySelection()
    si.selectAll()

class _SectionStreamableContent(_InterfaceSection):
  '''
  A class that populates a StreamableContent interface section.

  @ivar streams_model: Data model for available streams.
  @type streams_model: gtk.ListStore
  '''
  interface_name = 'StreamableContent'

  def init(self, glade_xml):
    '''
    Initialization that is specific to the StreamableContent interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    # configure streamable content tree view
    treeview = glade_xml.get_widget('treeview_streams')
    self.streams_model = gtk.ListStore(str, str)
    treeview.set_model(self.streams_model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('Content type'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=0)
    treeview.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn(_('URI'))
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=1)
    treeview.append_column(tvc)

  def populateUI(self, acc):
    '''
    Populate the StreamableContent section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    sci = acc.queryStreamableContent()

    for content_type in sci.getContentTypes():
      self.streams_model.append([content_type,
                                 sci.getURI(content_type)])
  
  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.streams_model.clear()

class _SectionTable(_InterfaceSection):
  '''
  A class that populates a Selection interface section.

  @ivar selected_frame: Container frame for selected cell info.
  @type selected_frame: gtk.Frame
  @ivar caption_label: Caption label.
  @type caption_label: gtk.Label
  @ivar summary_label: Summary label.
  @type summary_label: gtk.Label
  @ivar rows_label: Rows label.
  @type rows_label: gtk.Label
  @ivar columns_label: Columns label.
  @type columns_label: gtk.Label
  @ivar srows_label: Selected rows label.
  @type srows_label: gtk.Label
  @ivar scolumns_label: Scolumns label.
  @type scolumns_label: gtk.Label
  @ivar row_ext_label: Row extents label.
  @type row_ext_label: gtk.Label
  @ivar col_ext_label: Column extents label.
  @type col_ext_label: gtk.Label
  @ivar hrow_button: Row header button.
  @type hrow_button: gtk.Button
  @ivar hcol_button: Column header button.
  @type hcol_button: gtk.Button
  @ivar cell_button: Cell button.
  @type cell_button: gtk.Button
  '''
  interface_name = 'Table'
  def init(self, glade_xml):
    '''
    Initialization that is specific to the Table interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    glade_xml.signal_autoconnect(self)
    self.selected_frame = glade_xml.get_widget('selected_cell_frame')
    self.caption_label = glade_xml.get_widget('table_caption_label')
    self.summary_label = glade_xml.get_widget('table_summary_label')
    self.rows_label = glade_xml.get_widget('table_rows_label')
    self.columns_label = glade_xml.get_widget('table_columns_label')
    self.srows_label = glade_xml.get_widget('table_srows_label')
    self.scolumns_label = glade_xml.get_widget('table_scolumns_label')
    self.row_ext_label = glade_xml.get_widget('table_row_extents')
    self.col_ext_label = glade_xml.get_widget('table_column_extents')
    self.col_ext_label = glade_xml.get_widget('table_column_extents')
    self.hrow_button = glade_xml.get_widget('table_hrow_button')
    self.hcol_button = glade_xml.get_widget('table_hcol_button')
    self.cell_button = glade_xml.get_widget('table_cell_button')

  def populateUI(self, acc):
    '''
    Populate the Table section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    ti = acc.queryTable()
    self.selected_frame.set_sensitive(False)
    for attr, label in [(ti.caption, self.caption_label),
                        (ti.summary, self.summary_label),
                        (ti.nRows, self.rows_label),
                        (ti.nColumns, self.columns_label),
                        (ti.nSelectedRows, self.srows_label),
                        (ti.nSelectedColumns, self.scolumns_label)]:
      label.set_text(str(attr))
    self.registerEventListener(self._accEventTable,
                               'object:active-descendant-changed')

  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    self.caption_label.set_text('')
    self.summary_label.set_text('')
    self.rows_label.set_text('')
    self.columns_label.set_text('')
    self.srows_label.set_text('')
    self.scolumns_label.set_text('')
    self.row_ext_label.set_text('')
    self.col_ext_label.set_text('')
    self.col_ext_label.set_text('')
    self.hrow_button.set_label('')
    self.hcol_button.set_label('')
    self.cell_button.set_label('')


  def _accEventTable(self, event):
    '''
    Callback for 'object:active-descendant-changed' to detect selected cell
    changes.
    
    @param event: The event that triggered the callback.
    @type event: Accessibility.Event
    '''
    if self.node.acc != event.source:
      return

    acc = event.source
    ti = acc.queryTable()
    self.selected_frame.set_sensitive(True)
    is_cell, row, column, rextents, cextents, selected = \
        ti.getRowColumnExtentsAtIndex(event.any_data.getIndexInParent())

    for attr, label in [(rextents, self.row_ext_label),
                             (cextents, self.col_ext_label),
                             (ti.nSelectedRows, self.srows_label),
                             (ti.nSelectedColumns, self.scolumns_label)]:
      label.set_text(str(attr))

    for desc, acc, button in [(ti.getRowDescription(row), 
                               ti.getRowHeader(row),
                               self.hrow_button),
                              (ti.getColumnDescription(column), 
                               ti.getColumnHeader(column),
                               self.hcol_button),
                              ('%s (%s, %s)' % (event.any_data, row, column), 
                               event.any_data,
                               self.cell_button)]:
      button.set_label(str(desc or '<no description>'))
      button.set_sensitive(bool(acc))
      button.set_data('acc', acc)
        
  def _onTableButtonClicked(self, button):
    '''
    Callback for buttons that represent headers. 
    Will make the header the main application's selection.

    @param button: Button that triggered event.
    @type button: gtk.Button
    '''
    self.node.update(button.get_data('acc'))

class _SectionText(_InterfaceSection):
  '''
  A class that populates a Text interface section.

  @ivar attr_model: Data model for text attributes.
  @type attr_model: gtk.ListStore
  @ivar offset_spin: Offset spinner.
  @type offset_spin: gtk.SpinButton
  @ivar text_view: Text view of provided text.
  @type text_view: gtk.TextView
  @ivar text_buffer: Text buffer of provided text.
  @type text_buffer: gtk.TextBuffer
  @ivar toggle_defaults: Toggle button for viewing default text attributes.
  @type toggle_defaults: gtk.CheckButton
  @ivar label_start: Label for current attributes start offset.
  @type label_start: gtk.Label
  @ivar label_end: Label for current attributes end offset.
  @type label_end: gtk.Label
  @ivar _text_insert_handler: Handler ID for text insert events.
  @type _text_insert_handler: integer
  @ivar _text_delete_handler: Handler ID for text delete events.
  @type _text_delete_handler: integer
  @ivar outgoing_calls: Cached outgoing calls to avoid circular event 
  invocation.
  @type outgoing_calls: dictionary
  '''
  interface_name = 'Text'
  def init(self, glade_xml):
    '''
    Initialization that is specific to the Text interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    glade_xml.signal_autoconnect(self)
    # configure text attribute tree view
    treeview = glade_xml.get_widget('treeview_text_attr')
    self.attr_model = gtk.ListStore(str, str)
    treeview.set_model(self.attr_model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=0)
    treeview.append_column(tvc)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=1)
    treeview.append_column(tvc)

    self.offset_spin = glade_xml.get_widget('spinbutton_text_offset')
    self.text_view = glade_xml.get_widget('textview_text')
    self.text_buffer = self.text_view.get_buffer()
    self.toggle_defaults = glade_xml.get_widget('checkbutton_text_defaults')
    self.label_start = glade_xml.get_widget('label_text_attr_start')
    self.label_end = glade_xml.get_widget('label_text_attr_end')

    self._text_insert_handler = 0
    self._text_delete_handler = 0

    mark = self.text_buffer.create_mark('attr_mark', 
                                        self.text_buffer.get_start_iter(), True)
    self.text_buffer.create_tag('attr_region', foreground='red')

    self.text_buffer.connect('mark-set', self._onTextMarkSet)

    mark.set_visible(True)


    self.text_buffer.connect('modified-changed', 
                             self._onTextModified)
    self.text_buffer.connect('notify::cursor-position', 
                             self._onTextCursorMove)

    self.text_buffer.set_modified(False)

    # Initialize fifos to help eliminate the viscous cycle of signals.
    # It would be nice if we could just block/unblock it like in gtk, but
    # since it is IPC, asynchronous and not atomic, we are forced to do this.
    self.outgoing_calls = {'itext_insert': self.CallCache(),
                           'itext_delete': self.CallCache()}

  def populateUI(self, acc):
    '''
    Populate the Text section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    self.offset_spin.set_value(0)

    ti = acc.queryText()

    text = ti.getText(0, ti.characterCount)
    self.text_buffer.set_text(text)

    self.offset_spin.get_adjustment().upper = ti.characterCount

    self.popTextAttr(offset=0)

    try:
      eti = acc.queryEditableText()
    except:
      eti = None

    expander_label = self.expander.get_label_widget()
    label_text = expander_label.get_label()
    label_text = label_text.replace(_(' <i>(Editable)</i>'),'')
    if eti:
      label_text += _(' <i>(Editable)</i>')
      self.text_view.set_editable(True)
    else:
      self.text_view.set_editable(False)
    expander_label.set_label(label_text)

    self._text_insert_handler = self.text_buffer.connect('insert-text', 
                                                         self._onITextInsert)
    self._text_delete_handler = self.text_buffer.connect('delete-range', 
                                                         self._onITextDelete)

    self.registerEventListener(self._accEventText, 
                               'object:text-changed')

  def clearUI(self):
    '''
    Clear all section-specific data.
    '''
    if self._text_insert_handler:
      self.text_buffer.disconnect(self._text_insert_handler)
      self._text_insert_handler = 0
    if self._text_delete_handler:
      self.text_buffer.disconnect(self._text_delete_handler)
      self._text_delete_handler = 0

    self.offset_spin.set_value(0)
    self.label_start.set_text('')
    self.label_end.set_text('')
    self.text_buffer.set_text('')
    self.attr_model.clear()

  def _attrStringToDict(self, attr_string):
    '''
    Convinience method for converting attribute strings to dictionaries.
    
    @param attr_string: "key:value" pairs seperated by semi-colons.
    @type attr_string: string
    
    @return: Dictionary of attributes
    @rtype: dictionary
    '''
    if not attr_string:
      return {}
    attr_dict = {}
    for attr_pair in attr_string.split('; '):
      key, value = attr_pair.split(':')
      attr_dict[key] = value
    return attr_dict

  def _onTextModified(self, text_buffer):
    '''
    Callback that is triggered when the main text buffer is modified.
    Allows to adjust the spinners bounds accordingly.
    
    @param text_buffer: The section's main text buffer.
    @type text_buffer: gtk.TextBuffer
    '''
    self.offset_spin.get_adjustment().upper = text_buffer.get_char_count()
    text_buffer.set_modified(False)

  def _onTextMarkSet(self, text_buffer, iter, text_mark):
    '''
    Callback that is triggered when the attribute mark is moved to
    allow repopulation of the attributes view.
    
    @param text_buffer: The section's main text buffer.
    @type text_buffer: gtk.TextBuffer
    @param iter: Text iter of the new mark position.
    @type iter: gtk.TextIter
    @param text_mark: The text mark that was moved.
    @type text_mark: gtk.TextMark
    '''
    self.popTextAttr()

  def _onTextSpinnerChanged(self, spinner):
    '''
    Callback for hen the spinner's value changes. 
    Moves attribute mark accordingly.
    
    @param spinner: The marker offset spinner.
    @type spinner: gtk.SpinButton
    '''
    iter = self.text_buffer.get_iter_at_offset(int(self.offset_spin.get_value()))
    self.text_buffer.move_mark_by_name('attr_mark', iter)    

  def _onDefaultsToggled(self, toggle_button):
    '''
    Callback for when the "defaults" checkbutton is toggled. Re-populates
    attributes view.
    
    @param toggle_button: The defaults checkbutton
    @type toggle_button: gtk.CheckButton
    '''
    self.popTextAttr()

  def popTextAttr(self, offset=None):
    '''
    Populate the attributes view with attributes at the given offset, or at 
    the attribute mark.

    @param offset: Offset of wanted attributes. If none is given, 
    use attribute mark's offset.
    @type offset: integer
    '''
    try:
      ti = self.node.acc.queryText()
    except:
      return

    if offset is None:
      mark = self.text_buffer.get_mark('attr_mark')
      iter = self.text_buffer.get_iter_at_mark(mark)
      offset = iter.get_offset()

    show_default = self.toggle_defaults.get_active()
    attr, start, end = ti.getAttributes(offset)
    if show_default:
      def_attr = ti.getDefaultAttributes()
      attr_dict = self._attrStringToDict(def_attr)
      attr_dict.update(self._attrStringToDict(attr))
    else:
      attr_dict = self._attrStringToDict(attr)

    attr_list = attr_dict.keys()
    attr_list.sort()

    self.attr_model.clear()
    for attr in attr_list:
      self.attr_model.append([attr, attr_dict[attr]])

    self.text_buffer.remove_tag_by_name(
      'attr_region', 
      self.text_buffer.get_start_iter(),
      self.text_buffer.get_end_iter())
    self.text_buffer.apply_tag_by_name(
      'attr_region',
      self.text_buffer.get_iter_at_offset(start),
      self.text_buffer.get_iter_at_offset(end))
                                  
    self.label_start.set_markup('<i>Start: %d</i>' % start)
    self.label_end.set_markup('<i>End: %d</i>' % end)

  def _onTextViewPressed(self, widget, event):
    '''
    Update spin button in the case that the textview was clicked.
    Once the spin button's value changes, it's own callback fires which
    re-populates the attribute view.
    
    @param widget: The widget that recived the click event, 
    typically the text view.
    @type widget: gtk.Widget
    @param event: The click event.
    @type event: gtk.gdk.Event
    '''
    if event.button != 1:
      return

    x, y = event.get_coords()
    x, y = self.text_view.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET,
                                                   int(x), int(y))
    iter = self.text_view.get_iter_at_location(x, y)
     
    self.offset_spin.set_value(iter.get_offset())

  def _onTextCursorMove(self, text_buffer, param_spec):
    '''
    Update spinner when input cursor moves.
    
    @param text_buffer: The section's main text buffer.
    @type text_buffer: gtk.TextBuffer
    @param param_spec: Some gobject crud
    @type param_spec: object
    '''
    self.offset_spin.set_value(text_buffer.get_property('cursor-position'))

  def _accEventText(self, event):
    '''
    Callback for accessible text changes. Updates the text buffer accordingly.
    
    @param event: Event that triggered thi callback.
    @type event: Accessibility.Event
    '''
    if self.node.acc != event.source:
      return

    if event.type.major == 'text-changed':
      text_iter = self.text_buffer.get_iter_at_offset(event.detail1)
      if event.type.minor == 'insert':
        call = (event.detail1, event.any_data, event.detail2)
        if self.outgoing_calls['itext_insert'].isCached(call):
          return
        self.text_buffer.handler_block(self._text_insert_handler)
        self.text_buffer.insert(text_iter, event.any_data)
        self.text_buffer.handler_unblock(self._text_insert_handler)
           
      elif event.type.minor == 'delete':
        call = (event.detail1, event.detail2)
        if self.outgoing_calls['itext_delete'].isCached(call):
          return
        text_iter_end = \
            self.text_buffer.get_iter_at_offset(event.detail1 + event.detail2)
        self.text_buffer.handler_block(self._text_delete_handler)
        self.text_buffer.delete(text_iter, text_iter_end)
        self.text_buffer.handler_unblock(self._text_delete_handler)
     
  def _onITextInsert(self, text_buffer, iter, text, length):
    '''
    Callback for text inserts in the text buffer. Sends changes to examined 
    accessible.
    
    @param text_buffer: The section's main text buffer.
    @type text_buffer: gtk.TextBuffer
    @param iter: Text iter in which the insert occured.
    @type iter: gtk.TextIter
    @param text: The text that was inserted
    @type text: string
    @param length: The length of theinserted text.
    @type length: integer
    '''
    try:
      eti = self.node.acc.queryEditableText()
    except:
      return

    call = (iter.get_offset(), text, length)
    
    self.outgoing_calls['itext_insert'].append(call)
    eti.insertText(*call)

  def _onITextDelete(self, text_buffer, start, end):
    '''
    Callback for text deletes in the text buffer. Sends changes to examined 
    accessible.
    
    @param text_buffer: The section's main text buffer.
    @type text_buffer: gtk.TextBuffer
    @param start: The start offset of the delete action.
    @type start: integer
    @param end: The end offset of the delete action.
    @type end: integer
    '''
    try:
      eti = self.node.acc.queryEditableText()
    except:
      return

    call = (start.get_offset(), end.get_offset())
    
    self.outgoing_calls['itext_delete'].append(call)
    eti.deleteText(*call)

  def _onTextFocusChanged(self, text_view, event):
    '''
    Callback for leaving and entering focus from the textview,
    it hides/shows the attribute marker. When the textview has focus
    there is no need for the marker to be visible because of th input
    cursor.

    @param text_view: The text view that is being entered or leaved.
    @type text_view: gtk.TextView
    @param event: The focus event.
    @type event: gtk.gdk.Event
    '''
    mark = self.text_buffer.get_mark('attr_mark')
    mark.set_visible(not event.in_)
      
  class CallCache(list):
    '''
    A list derivative that provides a method for checking if something
    is in the list and removing it at the same time.
    '''
    def isCached(self, obj):
      '''
      Checks if a certain object is in this list instance. If it is, return 
      True and remove it.
      
      @param obj: Object to check for.
      @type obj: object
      
      @return: True if it is in the list.
      @rtype: boolean
      '''
      if obj in self:
        self.remove(obj)
        return True
      else:
        return False

class _SectionValue(_InterfaceSection):
  '''
  A class that populates a Value interface section.

  @ivar spinbutton: Value spinner.
  @type spinbutton: gtk.SpinButton
  @ivar label_max: Label of maximal value.
  @type label_max: gtk.Label
  @ivar label_min: Label of minimal value.
  @type label_min: gtk.Label
  @ivar label_inc: Label of minimal value increment.
  @type label_inc: gtk.Label
  '''
  interface_name = 'Value'
  def init(self, glade_xml):
    '''
    Initialization that is specific to the Value interface 
    (construct data models, connect signals to callbacks, etc.)
    
    @param glade_xml: Interface viewer glade xml.
    @type glade_xml: gtk.glade.XML
    '''
    glade_xml.signal_autoconnect(self)
    self.spinbutton = glade_xml.get_widget('spinbutton_value')
    self.label_max = glade_xml.get_widget('label_value_max')
    self.label_min = glade_xml.get_widget('label_value_min')
    self.label_inc = glade_xml.get_widget('label_value_inc')
    self.registerEventListener(self._accEventValue, 
                               'object:value-changed')
    
  def populateUI(self, acc):
    '''
    Populate the Value section with relevant data of the 
    currently selected accessible.
    
    @param acc: The currently selected accessible.
    @type acc: Accessibility.Accessible
    '''
    vi = acc.queryValue()
    self.label_max.set_text(str(vi.maximumValue))
    self.label_min.set_text(str(vi.minimumValue))
    self.label_inc.set_text(str(vi.minimumIncrement))

    minimumIncrement = vi.minimumIncrement
    digits = 0

    while minimumIncrement - int(minimumIncrement) != 0:
      digits += 1
      minimumIncrement *= 10

    self.spinbutton.set_range(vi.minimumValue, vi.maximumValue)
    self.spinbutton.set_value(vi.currentValue)
    self.spinbutton.set_digits(digits)
   
  def _onValueSpinnerChange(self, spinner):
    '''
    Callback for spinner changes. Updates accessible.
    
    @param spinner: The Value spinner
    @type spinner: gtk.SpinButton
    '''
    vi = self.node.acc.queryValue()
    vi.currentValue = spinner.get_value()

  def _accEventValue(self, event):
    '''
    Callback for value changes from the accessible. Update spin button.
    
    @param event: The event that triggered the callback.
    @type event: Accessibility.Event
    '''
    if self.node.acc != event.source:
      return
    vi = self.node.acc.queryValue()
    if self.spinbutton.get_value() != vi.currentValue:
      self.spinbutton.set_value(vi.currentValue)
