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
  plugin_name = N_('Interface Viewer')
  plugin_name_localized = _(plugin_name)
  plugin_description = N_('Allows viewing of various interface properties')
  def init(self):
    self.main_xml = gtk.glade.XML(GLADE_FILE, 'iface_view_frame')
    frame = self.main_xml.get_widget('iface_view_frame')
    self.plugin_area.add(frame)
    self.sections = {
      'Accessible' : _SectionAccessible(self.main_xml, self.node),
      'Action' : _SectionAction(self.main_xml, self.node),
      'Application' : _SectionApplication(self.main_xml, self.node),
      'Component' : _SectionComponent(self.main_xml, self.node),
      'Document' : _SectionDocument(self.main_xml, self.node),
      'Hypertext' : _SectionHypertext(self.main_xml, self.node),
      'Image' : _SectionImage(self.main_xml, self.node),
      'Selection' : _SectionSelection(self.main_xml, self.node),
      'StreamableContent' : _SectionStreamableContent(self.main_xml, self.node),
      'Table' : _SectionTable(self.main_xml, self.node)}

  def _getInterfaces(self, acc):
    interfaces = []
    for func in [getattr(acc, f) for f in dir(acc) if f.startswith('query')]:
      try:
        func()
      except:
        continue
      else:
        interfaces.append(func.func_name.replace('query', ''))
    interfaces.sort()
    return interfaces

  def onAccChanged(self, acc):
    interfaces = self._getInterfaces(acc)
    for interface_name, section_obj in self.sections.iteritems():
      section_obj.disable()
      print interfaces, interface_name
      if interface_name in interfaces:
        print 'populating', interface_name
        section_obj.enable(acc)

  def close(self):
    pass

class _InterfaceSection(object):
  '''
  An abstract class that defines the interface for interface sections.

  @cvar interface_name: Name of interface this section is for.
  @type interface_name: string
  '''
  interface_name = None
  def __init__(self, glade_xml, node):
    self.node = node
    self.expander = \
        glade_xml.get_widget('expander_%s' % self.interface_name.lower())
    self._setExpanderChildrenSensitive(self.expander, False)
    self.init(glade_xml)
    self.event_listeners = []

  def init(self, glade_xml):
    pass

  def enable(self, acc):
    self._setExpanderChildrenSensitive(self.expander, True)
    self.populateUI(acc)

  def populateUI(self, acc):
    pass

  def disable(self):
    self._setExpanderChildrenSensitive(self.expander, False)
    for client, event_names in self.event_listeners:
      pyatspi.Registry.deregisterEventListener(client, *event_names)
    self.clearUI()

  def clearUI(self):
    pass

  def _setExpanderChildrenSensitive(self, expander, sensitive):
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
    model, rows = selection.get_selected_rows()
    something_is_selected = bool(rows)
    return something_is_selected

  def _onViewSelectionChanged(self, selection, *widgets):
    for widget in widgets:
      widget.set_sensitive(self._isSelectedInView(selection))
      
  def registerEventListener(self, client, *event_names):
    pyatspi.Registry.registerEventListener(client, *event_names)
    self.event_listeners.append((client, event_names))

class _SectionAccessible(_InterfaceSection):
  '''
  A class that populates an accessible interface section.
  '''
  interface_name = 'Accessible'
  def init(self, glade_xml):
    glade_xml.signal_autoconnect(self)
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
    selection.set_select_function(self._relationSelectFunc, full=True)
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

    pyatspi.Registry.registerEventListener(self._accEventState, 
                                           'object:state-changed')

  def populateUI(self, acc):
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
    self.relations_model.clear()
    self.states_model.clear()
    self.attr_model.clear()

  def _relationCellDataFunc(self, tvc, cellrenderer, model, iter):
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

  def _relationSelectFunc(self, selection, model, path, is_selected):
    return not len(path) == 1

  def _onRelationShow(self, relations_view, *more_args):
    selection = relations_view.get_selection()
    model, iter = selection.get_selected()
    if iter:
      acc = model[iter][2]
      if acc:
        self.node.update(acc)
  
  def _accEventState(self, event):
     if self.node.acc == event.source:
       self.states_model.clear()
       states = [pyatspi.stateToString(s) for s in \
                   self.node.acc.getState().getStates()]
       states.sort()
       map(self.states_model.append, [[state] for state in states])        


class _SectionAction(_InterfaceSection):
  interface_name = 'Action'
  def init(self, glade_xml):
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
    ai = acc.queryAction()
    for i in range(ai.nActions):
      self.actions_model.append([i, ai.getName(i),
                                 ai.getDescription(i),
                                 ai.getKeyBinding(i)])

  def clearUI(self):
    self.actions_model.clear()

  def _onActionRowActivated(self, treeview, path, view_column):
    action_num = self.actions_model[path][0]
    ai = self.node.acc.queryAction()
    ai.doAction(action_num)

  def _onActionClicked(self, button):
    actions_model, iter = self.action_selection.get_selected()
    action_num = actions_model[iter][0]
    ai = self.node.acc.queryAction()
    ai.doAction(action_num)

class _SectionApplication(_InterfaceSection):
  interface_name = 'Application'
  def init(self, glade_xml):
    self.label_id = glade_xml.get_widget('label_app_id')
    self.label_tk = glade_xml.get_widget('label_app_tk')
    self.label_version = glade_xml.get_widget('label_app_version')
  
  def populateUI(self, acc):
    ai = acc.queryApplication()
    self.label_id.set_text(repr(ai.id))
    self.label_tk.set_text(ai.toolkitName)
    self.label_version.set_text(ai.version)

  def clearUI(self):
    self.label_id.set_text('')
    self.label_tk.set_text('')
    self.label_version.set_text('')

class _SectionComponent(_InterfaceSection):
  interface_name = 'Component'
  def init(self, glade_xml):
    self.label_posrel = glade_xml.get_widget('absolute_position_label')
    self.label_posabs = glade_xml.get_widget('relative_position_label')
    self.label_size = glade_xml.get_widget('size_label')
    self.label_layer = glade_xml.get_widget('layer_label')
    self.label_zorder = glade_xml.get_widget('zorder_label')
    self.label_alpha = glade_xml.get_widget('alpha_label')

  def populateUI(self, acc):
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
    self.label_posrel.set_text('')
    self.label_posabs.set_text('')
    self.label_size.set_text('')
    self.label_layer.set_text('')
    self.label_zorder.set_text('')
    self.label_alpha.set_text('')

  def _accEventComponent(self, event):
    if event.source == self.node.acc:
      self.populateUI(event.source)


class _SectionDocument(_InterfaceSection):
  interface_name = 'Document'
  def init(self, glade_xml):
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
    self.attr_model.clear()
    self.label_locale.set_text('')

class _SectionHypertext(_InterfaceSection):
  interface_name = 'Hypertext'
  def init(self, glade_xml):
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
    self.links_model.clear()

  def _onLinkShow(self, link_view, *more_args):
    selection = link_view.get_selection()
    model, iter = selection.get_selected()
    if iter:
      acc = model[iter][6]
      if acc:
        self.node.update(acc)


class _SectionImage(_InterfaceSection):
  interface_name = 'Image'

  def init(self, glade_xml):
    self.label_pos = glade_xml.get_widget('img_position_label')
    self.label_size = glade_xml.get_widget('img_size_label')

  def populateUI(self, acc):
    ii = acc.queryImage()

    bbox = ii.getImageExtents(pyatspi.DESKTOP_COORDS)
    self.label_pos.set_text('%d, %d' % (bbox.x, bbox.y))
    self.label_size.set_text('%dx%d' % (bbox.width, bbox.height))

  def clearUI(self):
    self.label_pos.set_text('')
    self.label_size.set_text('')

class _SectionSelection(_InterfaceSection):
  interface_name = 'Selection'

  def init(self, glade_xml):
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
    show_button = glade_xml.get_widget('button_selection_clear')
    show_button.set_sensitive(self._isSelectedInView(self.sel_selection))
    self.sel_selection.connect('changed', 
                               self._onViewSelectionChanged, show_button)
    self.sel_selection.connect('changed', 
                               self._onSelectionSelected)
    self.button_select_all = glade_xml.get_widget('button_select_all')

  def populateUI(self, acc):
    si = acc.querySelection()

    # I wish there were a better way of knowing if multiple 
    # selections are possible.
    multiple_selections = si.selectAll()
    si.clearSelection

    self.button_select_all.set_sensitive(multiple_selections)

    if multiple_selections:
      self.sel_selection.set_mode = gtk.SELECTION_MULTIPLE
    else:
      self.sel_selection.set_mode = gtk.SELECTION_SINGLE

    for child in acc:
      if child is not None:
        state = child.getState()
        if state.contains(pyatspi.STATE_SELECTABLE):
          self.sel_model.append([getIcon(child),child.name, child])
    
  def _onSelectionSelected(self, selection):
    si = self.node.acc.querySelection()

    model, paths = selection.get_selected_rows()
    selected_children = [path[0] for path in paths]
    
    for child_index in range(len(self.node.acc)):
      if child_index in selected_children:
        si.selectChild(child_index)
      else:
        si.deselectChild(child_index)

  def clearUI(self):
    self.sel_model.clear()
  
  def _onSelectionClear(self, widget):
    si = self.node.acc.querySelection()

    self.sel_selection.unselect_all()
    si.clearSelection()

  def _onSelectAll(self, widget):
    si = self.node.acc.querySelection()

    self.sel_selection.select_all()
    si.selectAll()

class _SectionStreamableContent(_InterfaceSection):
  interface_name = 'StreamableContent'
  def init(self, glade_xml):
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
    sci = acc.queryStreamableContent()

    for content_type in sci.getContentTypes():
      self.streams_model.append([content_type,
                                 sci.getURI(content_type)])
  
  def clearUI(self):
    self.streams_model.clear()

class _SectionTable(_InterfaceSection):
  interface_name = 'Table'
  def init(self, glade_xml):
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
    self.caption_label.set_text('')
    self.summary_label.set_text('')
    self.rows_label.set_text('')
    self.columns_label.set_text('')
    self.srows_label.set_text('')
    self.scolumns_label.set_text('')
    self.row_ext.set_text('')
    self.col_ext.set_text('')
    self.col_ext.set_text('')
    self.hrow_button.set_text('')
    self.hcol_button.set_text('')
    self.cell_button.set_text('')


  def _accEventTable(self, event):
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
    self.node.update(button.get_data('acc'))
