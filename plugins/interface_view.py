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
import accerciser.plugin
from accerciser.icons import getIcon
from accerciser.i18n import _

GLADE_FILE = os.path.join(os.path.dirname(__file__), 
                          'interface_view.glade')

class CallCache(list):
   def isCached(self, obj):
      if obj in self:
         self.remove(obj)
         return True
      else:
         return False

class InterfaceViewer(accerciser.plugin.ViewportPlugin):
  plugin_name = 'Interface viewer'
  plugin_description = 'Allows viewing of various interfac propertiesXS'
  def init(self):
    self.main_xml = gtk.glade.XML(GLADE_FILE, 'iface_view_frame')
    frame = self.main_xml.get_widget('iface_view_frame')
    self.plugin_area.add(frame)

    self.role = self.main_xml.get_widget('role')
    self.main_xml.signal_autoconnect(self)
    self._initTreeViews()

    vbox_expanders = self.main_xml.get_widget('vbox_ifaces')
    for expander in vbox_expanders.get_children():
      if isinstance(expander, gtk.Expander):
        expander.connect('notify::expanded', self._onIfaceExpanded)
        expander.connect('focus-in-event', self._onScrollToFocus)

    self.event_manager = pyLinAcc.Event.Manager()
    self.event_manager.addClient(self._accEventText, 
                                 'object:text-changed')
    self.event_manager.addClient(self._accEventValue, 
                                 'object:property-change:accessible-value')
    self.event_manager.addClient(self._accEventState, 
                                 'object:state-changed')
    self.event_manager.addClient(self._accEventComponent, 
                                 'object:bounds-changed',
                                 'object:visible-data-changed')
    self.event_manager.addClient(self._accEventTable,
                                 'object:active-descendant-changed')
    # Initialize fifos to help eliminate the viscous cycle of signals.
    # It would be nice if we could just block/unblock it like in gtk, but
    # since it is IPC, asynchronous and not atomic, we are forced to do this.
    self.outgoing_calls = {'itext_insert': CallCache(),
                           'itext_delete': CallCache()}
    self._textInit()
  
  def close(self):
    self.event_manager.close()


  def _initTreeViews(self):
    # configure text attribute tree view
    treeview = self.main_xml.get_widget('treeview_text_attr')
    model = gtk.ListStore(str, str)
    treeview.set_model(model)
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

    # configure accessible attributes tree view
    treeview = self.main_xml.get_widget('accattrib_view')
    model = gtk.ListStore(str, str)
    treeview.set_model(model)
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

    # configure document attributes tree view
    treeview = self.main_xml.get_widget('docattrib_view')
    model = gtk.ListStore(str, str)
    treeview.set_model(model)
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

    # configure relations tree view
    treeview = self.main_xml.get_widget('relations_view')
    model = gtk.TreeStore(gtk.gdk.Pixbuf, str, object)
    treeview.set_model(model)
    crt = gtk.CellRendererText()
    crp = gtk.CellRendererPixbuf()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crp, False)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crp, pixbuf=0)
    tvc.set_attributes(crt, text=1)
    tvc.set_cell_data_func(crt, self._relationCellDataFunc)
    tvc.set_cell_data_func(crp, self._relationCellDataFunc)
    treeview.append_column(tvc)
    # preset the different bg colors
    style = gtk.Style ()
    self.header_bg = style.bg[gtk.STATE_NORMAL]
    self.relation_bg = style.base[gtk.STATE_NORMAL]
    selection = treeview.get_selection()
    selection.set_select_function(self._relationSelectFunc, full=True)

    # configure selection tree view
    treeview = self.main_xml.get_widget('treeview_selection')
    model = gtk.ListStore(gtk.gdk.Pixbuf, str, object)
    treeview.set_model(model)
    crt = gtk.CellRendererText()
    crp = gtk.CellRendererPixbuf()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crp, False)
    tvc.pack_start(crt, True)
    tvc.set_attributes(crp, pixbuf=0)
    tvc.set_attributes(crt, text=1)
    treeview.append_column(tvc)
    # connect selection changed signal
    selection = treeview.get_selection()
    selection.connect("changed", self._onSelectionSelected)

    # configure states tree view
    treeview = self.main_xml.get_widget('states_view')
    model = gtk.ListStore(str)
    treeview.set_model(model)
    crt = gtk.CellRendererText()
    tvc = gtk.TreeViewColumn()
    tvc.pack_start(crt, True)
    tvc.set_attributes(crt, text=0)
    treeview.append_column(tvc)

    # configure links tree view
    treeview = self.main_xml.get_widget('treeview_links')
    # It's a treestore because of potential multiple anchors
    model = gtk.TreeStore(int, # Link index
                          str, # Name
                          str, # Description
                          str, # URI
                          int, # Start offset
                          int, # End offset
                          object) # Anchor object
    treeview.set_model(model)
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

    # configure actions tree view
    treeview = self.main_xml.get_widget('treeview_action')
    model = gtk.ListStore(int, str, str, str)
    treeview.set_model(model)
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

    # configure streamable content tree view
    treeview = self.main_xml.get_widget('treeview_streams')
    model = gtk.ListStore(str, str)
    treeview.set_model(model)
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

  def _onScrollToFocus(self, widget, event):
    '''
    Scrolls a focused widget in a settings panel into view.
    
    @param widget: Widget that has the focus
    @type widget: gtk.Widget
    @param direction: Direction constant, ignored
    @type direction: integert
    '''
    x, y = widget.translate_coordinates(self.viewport, 0, 0)
    w, h = widget.size_request()
    vw, vh = self.allocation.width, self.allocation.height

    adj = self.viewport.get_vadjustment()
    if y+h > vh:
      adj.value += min((y+h) - vh + 3, y)
    elif y < 0:
      adj.value = max(adj.value + y, adj.lower)

  def _getInterfaces(self, acc):
    ints = []
    for func in (f for f in pyLinAcc.Interfaces.__dict__.values() 
                 if callable(f) and f.func_name.startswith('I')):
      try:
        i = func(acc)
      except Exception:
        pass
      else:
        ints.append(func.func_name[1:].lower())
    ints.sort()
    return ints

  def _getAllInterfaces(self):
     all_ifaces = filter(lambda s: s.startswith('I'),
                         dir(pyLinAcc.Interfaces))
     return [iface[1:].lower() for iface in all_ifaces]


  def onAccChanged(self, acc):
    '''
    Updates all GUI fields with strings representing the properties of the 
    selected accessible at the time it was selected. Does not automatically
    update when the accessible changes.
    '''
    
    try:
      name = acc.name
    except:
      name = ''
    try:
      role = acc.getRoleName()
    except Exception:
      role = ''
    try:
      rels = [pyLinAcc.relationToString(r.getRelationType()) 
              for r in acc.getRelationSet()]
      rels.sort()
    except Exception:
      rels = []
      
    available_ifaces = self._getInterfaces(acc)
    
    all_ifaces = self._getAllInterfaces()

    for iface in all_ifaces:
      expander = self.main_xml.get_widget('expander_'+iface)
      if expander is None:
        continue
      if iface in available_ifaces:
        self._setExpanderChildrenSensitive(expander, True)
        if expander.get_expanded():
          try:
            pop_func = getattr(self, 'popIface'+iface.capitalize())
          except AttributeError:
            print 'attr error', 'popIface'+iface.capitalize()
          pop_func(acc)
      else:
        self._setExpanderChildrenSensitive(expander, False)
        
    if name:
      role_name = ': '.join((role, name))
    else:
      role_name = role
      
    self.role.set_markup('<span size="large" weight="bold">%s</span>' % role_name)
    
  def _setExpanderChildrenSensitive(self, expander, sensitive):
    for child in expander.get_children():
      child.set_sensitive(sensitive)

  def _onIfaceExpanded(self, expander, param_spec):
    if not expander.get_expanded(): return
    iface = expander.name.replace('expander_', '')
    available_ifaces = self._getInterfaces(self.acc)
    if iface not in available_ifaces: return
    try:
      pop_func = getattr(self, 'popIface'+iface.capitalize())
    except AttributeError:
      return
    pop_func(self.acc)

##############################
# Accessible Interface
##############################

  def popIfaceAccessible(self,acc):
    states_view = self.main_xml.get_widget('states_view')
    states_model = states_view.get_model()
    accattrib_view = self.main_xml.get_widget('accattrib_view')
    attrib_model = accattrib_view.get_model()
    relations_view = self.main_xml.get_widget('relations_view')
    relations_model = relations_view.get_model()

    try:
      states = [pyLinAcc.stateToString(s) for s in acc.getState().getStates()]
      states.sort()
    except Exception:
      states = []

    states_model.clear()
    for state in states:
      states_model.append([state])
    
    attrib_model.clear()
    try:
      attribs = acc.getAttributes()
    except:
      attribs = None
    if attribs:
      for attr in attribs:
        name, value = attr.split(':', 1)
        attrib_model.append([name, value])

    relations_model.clear()
    relations = acc.getRelationSet()
    for relation in relations:
      r_type_name = repr(relation.getRelationType()).replace('RELATION_', '')
      r_type_name = r_type_name.replace('_', ' ').lower().capitalize()
      iter = relations_model.append(None, [None, r_type_name, None])
      for i in range(relation.getNTargets()):
        acc = relation.getTarget(0)
        relations_model.append(iter, [getIcon(acc), acc.name, acc])
    relations_view.expand_all()


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
     if self.acc != event.source:
        return
     self.popIfaceAccessible(self.acc)
     if 'action' in self._getInterfaces(self.acc):
        self.popIfaceAction(self.acc)



##############################
# Action Interface
##############################

  def popIfaceAction(self, acc):
    actions_view = self.main_xml.get_widget('treeview_action')
    actions_model = actions_view.get_model()
    
    actions_model.clear()

    ai = pyLinAcc.Interfaces.IAction(acc)

    for i in range(ai.nActions):
      actions_model.append([i, ai.getName(i),
                            ai.getDescription(i),
                            ai.getKeyBinding(i)])

  def _onActionRowActivated(self, treeview, path, view_column):
     actions_model = treeview.get_model()
     iter = actions_model.get_iter(path)
     action_num = actions_model.get_value(iter, 0)
     acc = self.acc
     ai = pyLinAcc.Interfaces.IAction(acc)
     ai.doAction(action_num)

##############################
# Application Interface
##############################

  def popIfaceApplication(self, acc):
    label_app_id = self.main_xml.get_widget('label_app_id')
    label_app_tk = self.main_xml.get_widget('label_app_tk')
    label_app_version = self.main_xml.get_widget('label_app_version')

    ai = pyLinAcc.Interfaces.IApplication(acc)

    label_app_id.set_text(repr(ai.id))
    label_app_tk.set_text(ai.toolkitName)
    label_app_version.set_text(ai.version)

##############################
# Component Interface
##############################

  def popIfaceComponent(self, acc):
    abs_label_pos = self.main_xml.get_widget('absolute_position_label')
    rel_label_pos = self.main_xml.get_widget('relative_position_label')
    label_size = self.main_xml.get_widget('size_label')
    label_layer = self.main_xml.get_widget('layer_label')
    label_zorder = self.main_xml.get_widget('zorder_label')
    label_alpha = self.main_xml.get_widget('alpha_label')
     
    ci = pyLinAcc.Interfaces.IComponent(acc)
     
    bbox = ci.getExtents(pyLinAcc.Constants.DESKTOP_COORDS)
    abs_label_pos.set_text('%d, %d' % (bbox.x, bbox.y))
    label_size.set_text('%dx%d' % (bbox.width, bbox.height))
    bbox = ci.getExtents(pyLinAcc.Constants.WINDOW_COORDS)
    rel_label_pos.set_text('%d, %d' % (bbox.x, bbox.y))
    layer = ci.getLayer()
    label_layer.set_text(repr(ci.getLayer()).replace('LAYER_',''))
    label_zorder.set_text(repr(ci.getMDIZOrder()))
    label_alpha.set_text(repr(ci.getAlpha()))

  def _accEventComponent(self, event):
     if self.acc != event.source:
        return
     self.popIfaceComponent(self.acc)

##############################
# Document Interface
##############################

  def popIfaceDocument(self, acc):
    docattrib_view = self.main_xml.get_widget('docattrib_view')
    label_locale = self.main_xml.get_widget('label_doc_locale')
    attrib_model = docattrib_view.get_model()

    di = pyLinAcc.Interfaces.IDocument(acc)

    label_locale.set_text(di.getLocale())

    attrib_model.clear()
    try:
      attribs = di.getAttributes()
    except:
      attribs = None
    if attribs:
      for attr in attribs:
        name, value = attr.split(':', 1)
        attrib_model.append([name, value])

##############################
# Hypertext Interface
##############################

  def popIfaceHypertext(self, acc):
    links_view = self.main_xml.get_widget('treeview_links')
    links_model = links_view.get_model()

    hti = pyLinAcc.Interfaces.IHypertext(acc)

    links_model.clear()
    for link_index in xrange(hti.getNLinks()):
      link = hti.getLink(link_index)
      iter = links_model.append(None,
                                [link_index, '', '', '',
                                 link.startIndex, link.endIndex, None])
      for anchor_index in xrange(link.nAnchors):
        acc_obj = link.getObject(anchor_index)
        links_model.append(iter,
                           [link_index, acc_obj.name, acc_obj.description,
                            link.getURI(anchor_index), 
                            link.startIndex, link.endIndex, acc_obj])
        if anchor_index == 0:
          links_model[iter][1] = acc_obj.name # Otherwise the link is nameless.
     

  def _onLinkShow(self, link_view, *more_args):
    selection = link_view.get_selection()
    model, iter = selection.get_selected()
    if iter:
      acc = model[iter][6]
      if acc:
        self.node.update(acc)
     
##############################
# Image Interface
##############################

  def popIfaceImage(self, acc):
    label_pos = self.main_xml.get_widget('img_position_label')
    label_size = self.main_xml.get_widget('img_size_label')

    ii = pyLinAcc.Interfaces.IImage(acc)

    bbox = ii.getImageExtents(pyLinAcc.Constants.DESKTOP_COORDS)
    label_pos.set_text('%d, %d' % (bbox.x, bbox.y))
    label_size.set_text('%dx%d' % (bbox.width, bbox.height))

##############################
# Selection Interface
##############################

  def popIfaceSelection(self, acc):
    selection_treeview = self.main_xml.get_widget('treeview_selection')
    button_select_all = self.main_xml.get_widget('button_select_all')
    selection_model = selection_treeview.get_model()
    selection_selection = selection_treeview.get_selection()
    
    selection_model.clear()

    si = pyLinAcc.Interfaces.ISelection(acc)

    # I wish there were a better way of knowing if multiple 
    # selections are possible.
    multiple_selections = si.selectAll()
    si.clearSelection

    button_select_all.set_sensitive(multiple_selections)

    if multiple_selections:
      selection_selection.set_mode = gtk.SELECTION_MULTIPLE
    else:
      selection_selection.set_mode = gtk.SELECTION_SINGLE

    for child in acc:
      if child is not None:
        state = child.getState()
        if state.contains(pyLinAcc.Constants.STATE_SELECTABLE):
          selection_model.append([getIcon(child),child.name, child])

  def _onSelectionSelected(self, selection):
     acc = self.acc
     try:
        si = pyLinAcc.Interfaces.ISelection(acc)
     except:
        return
     model, paths = selection.get_selected_rows()
     selected_children = [path[0] for path in paths]

     for child_index in range(len(acc)):
        if child_index in selected_children:
           si.selectChild(child_index)
        else:
           si.deselectChild(child_index)
  
  def _onSelectionClear(self, widget):
     acc = self.acc
     try:
        si = pyLinAcc.Interfaces.ISelection(acc)
     except:
        return
     selection_treeview = self.main_xml.get_widget('treeview_selection')
     selection_selection = selection_treeview.get_selection()

     selection_selection.unselect_all()
     si.clearSelection()

  def _onSelectAll(self, widget):
     acc = self.acc
     try:
        si = pyLinAcc.Interfaces.ISelection(acc)
     except:
        return
     selection_treeview = self.main_xml.get_widget('treeview_selection')
     selection_selection = selection_treeview.get_selection()

     selection_selection.select_all()
     si.selectAll()


##############################
# Streamable Content Interface
##############################

  def popIfaceStreamablecontent(self, acc):
    streams_view = self.main_xml.get_widget('treeview_streams')
    streams_model = streams_view.get_model()

    streams_model.clear()
    
    sci = pyLinAcc.Interfaces.IStreamableContent(acc)

    for content_type in sci.getContentTypes():
      streams_model.append([content_type,
                            sci.getURI(content_type)])

##############################
# Table Interface
##############################

  def popIfaceTable(self, acc):
    ti = pyLinAcc.Interfaces.ITable(acc)
    frame = self.main_xml.get_widget('selected_cell_frame')
    frame.set_sensitive(False)
    for attr, label_name in [(ti.caption, 'table_caption_label'),
                             (ti.summary, 'table_summary_label'),
                             (ti.nRows, 'table_rows_label'),
                             (ti.nColumns, 'table_columns_label'),
                             (ti.nSelectedRows, 'table_srows_label'),
                             (ti.nSelectedColumns, 'table_scolumns_label')]:
      label = self.main_xml.get_widget(label_name)
      label.set_text(str(attr))
  
  def _accEventTable(self, event):
    if self.acc != event.source:
      return
    
    try:
      ti = pyLinAcc.Interfaces.ITable(self.acc)
    except:
      return

    frame = self.main_xml.get_widget('selected_cell_frame')
    frame.set_sensitive(True)
    is_cell, row, column, rextents, cextents, selected = \
        ti.getRowColumnExtentsAtIndex(event.any_data.getIndexInParent())
    
    for attr, label_name in [(rextents, 'table_row_extents'),
                             (cextents, 'table_column_extents'),
                             (ti.nSelectedRows, 'table_srows_label'),
                             (ti.nSelectedColumns, 'table_scolumns_label')]:
      label = self.main_xml.get_widget(label_name)
      label.set_text(str(attr))           
    
    for desc, acc, button_name in [(ti.getRowDescription(row), 
                                    ti.getRowHeader(row),
                                    'table_hrow_button'),
                                   (ti.getColumnDescription(column), 
                                    ti.getColumnHeader(column),
                                    'table_hcol_button'),
                                   ('%s (%s, %s)' % (event.any_data, row, column), 
                                    event.any_data,
                                    'table_cell_button')]:
      button = self.main_xml.get_widget(button_name)
      button.set_label(str(desc or '<no description>'))
      button.set_sensitive(bool(acc))
      button.set_data('acc', acc)
        
  def _onTableButtonClicked(self, button):
    self.node.update(button.get_data('acc'))
    
##############################
# Text Interface
##############################

  def _textInit(self):
    spinbutton = self.main_xml.get_widget('spinbutton_text_offset')
    text_view = self.main_xml.get_widget('textview_text')
    text_buffer = text_view.get_buffer()
    checkbutton_defaults = self.main_xml.get_widget('checkbutton_text_defaults')

    text_buffer.connect('mark-set', self._onTextMarkSet)

    mark = text_buffer.create_mark('attr_mark', 
                                   text_buffer.get_start_iter(), True)
    mark.set_visible(True)

    text_buffer.create_tag('attr_region', foreground='red')

    text_buffer.connect('modified-changed', 
                        self._onTextModified, spinbutton)
    text_buffer.connect('notify::cursor-position', 
                        self._onTextCursorMove, spinbutton)

    text_buffer.set_modified(False)
    self._text_insert_handler = text_buffer.connect('insert-text', 
                                                    self._onITextInsert)
    self._text_delete_handler = text_buffer.connect('delete-range', 
                                                    self._onITextDelete)

  def popIfaceText(self, acc):
    spinbutton = self.main_xml.get_widget('spinbutton_text_offset')
    text_view = self.main_xml.get_widget('textview_text')
    checkbutton_defaults = self.main_xml.get_widget('checkbutton_text_defaults')
    text_buffer = text_view.get_buffer()
     
    spinbutton.set_value(0)

    ti = pyLinAcc.Interfaces.IText(acc)

    text = ti.getText(0, ti.characterCount)
    for handler_id in (self._text_delete_handler,
                       self._text_insert_handler):
      text_buffer.handler_block(handler_id)
    text_buffer.set_text(text)
    for handler_id in (self._text_delete_handler,
                       self._text_insert_handler):
      text_buffer.handler_unblock(handler_id)

    spinbutton.get_adjustment().upper = ti.characterCount

    self.popTextAttr(offset=0)

    try:
      eti = pyLinAcc.Interfaces.IEditableText(acc)
    except:
      eti = None

    expander = self.main_xml.get_widget('expander_text')

    if eti:
      expander.set_label('Text <i>(Editable)</i>')
      text_view.set_editable(True)
    else:
      expander.set_label('Text')
      text_view.set_editable(False)

  def _attrStringToDict(self, attr_string):
    if not attr_string:
      return {}
    attr_dict = {}
    for attr_pair in attr_string.split('; '):
      key, value = attr_pair.split(':')
      attr_dict[key] = value
    return attr_dict

  def _onTextModified(self, text_buffer, spinbutton):
    spinbutton.get_adjustment().upper = text_buffer.get_char_count()
    text_buffer.set_modified(False)

  def _onTextMarkSet(self, text_buffer, iter, text_mark):
    self.popTextAttr()

  def _onTextSpinnerChanged(self, spinner):
    text_view = self.main_xml.get_widget('textview_text')
    text_buffer = text_view.get_buffer()
    iter = text_buffer.get_iter_at_offset(int(spinner.get_value()))
    text_buffer.move_mark_by_name('attr_mark', iter)    

  def _onDefaultsToggled(self, toggle_button):
    self.popTextAttr()

  def popTextAttr(self, offset=None):
    text_view = self.main_xml.get_widget('textview_text')
    text_buffer = text_view.get_buffer()
    attr_treeview = self.main_xml.get_widget('treeview_text_attr')
    attr_model = attr_treeview.get_model()
    label_start = self.main_xml.get_widget('label_text_attr_start')
    label_end = self.main_xml.get_widget('label_text_attr_end')
    checkbutton_defaults = self.main_xml.get_widget('checkbutton_text_defaults')

    try:
      ti = pyLinAcc.Interfaces.IText(self.acc)
    except:
      label_start.set_markup('<i>Start: 0</i>')
      label_end.set_markup('<i>End: 0</i>')
      attr_model.clear()
      return

    if offset is None:
      mark = text_buffer.get_mark('attr_mark')
      iter = text_buffer.get_iter_at_mark(mark)
      offset = iter.get_offset()

    show_default = checkbutton_defaults.get_active()
    attr, start, end = ti.getAttributes(offset)
    if show_default:
      def_attr = ti.getDefaultAttributes()
      attr_dict = self._attrStringToDict(def_attr)
      attr_dict.update(self._attrStringToDict(attr))
    else:
      attr_dict = self._attrStringToDict(attr)

    attr_list = attr_dict.keys()
    attr_list.sort()

    attr_model.clear()
    for attr in attr_list:
      attr_model.append([attr, attr_dict[attr]])

    text_buffer.remove_tag_by_name('attr_region', 
                                   text_buffer.get_start_iter(),
                                   text_buffer.get_end_iter())
    text_buffer.apply_tag_by_name('attr_region',
                                  text_buffer.get_iter_at_offset(start),
                                  text_buffer.get_iter_at_offset(end))
                                  
    label_start.set_markup('<i>Start: %d</i>' % start)
    label_end.set_markup('<i>End: %d</i>' % end)

  def _onTextViewPressed(self, widget, event):
     if event.button != 1:
        return

     text_view = self.main_xml.get_widget('textview_text')
     spinbutton = self.main_xml.get_widget('spinbutton_text_offset')
     x, y = event.get_coords()
     x, y = text_view.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET,
                                              int(x), int(y))
     iter = text_view.get_iter_at_location(x, y)
     
     spinbutton.set_value(iter.get_offset())

  def _onTextCursorMove(self, text_buffer, param_spec, spinbutton):
    print 'cursor move'
    spinbutton.set_value(text_buffer.get_property('cursor-position'))

  def _accEventText(self, event):
     if self.acc != event.source:
        return

     if event.type.major == 'text-changed':
        text_view = self.main_xml.get_widget('textview_text')
        text_buffer = text_view.get_buffer()
        text_iter = text_buffer.get_iter_at_offset(event.detail1)
        if event.type.minor == 'insert':
           call = (event.detail1, event.any_data, event.detail2)
           if self.outgoing_calls['itext_insert'].isCached(call):
              return
           text_buffer.handler_block(self._text_insert_handler)
           text_buffer.insert(text_iter, event.any_data)
           text_buffer.handler_unblock(self._text_insert_handler)
           
        elif event.type.minor == 'delete':
           call = (event.detail1, event.detail2)
           if self.outgoing_calls['itext_delete'].isCached(call):
              return
           text_iter_end = text_buffer.get_iter_at_offset(event.detail1 + event.detail2)
           text_buffer.handler_block(self._text_delete_handler)
           text_buffer.delete(text_iter, text_iter_end)
           text_buffer.handler_unblock(self._text_delete_handler)
     
  def _onITextInsert(self, text_buffer, iter, text, length):
     acc = self.acc
     try:
        eti = pyLinAcc.Interfaces.IEditableText(acc)
     except:
        return

     call = (iter.get_offset(), text, length)

     self.outgoing_calls['itext_insert'].append(call)
     eti.insertText(*call)

  def _onITextDelete(self, text_buffer, start, end):
     acc = self.acc
     try:
        eti = pyLinAcc.Interfaces.IEditableText(acc)
     except:
        return

     call = (start.get_offset(), end.get_offset())

     self.outgoing_calls['itext_delete'].append(call)
     eti.deleteText(*call)

  def _onTextFocusChanged(self, text_view, event):
    text_buffer = text_view.get_buffer()
    mark = text_buffer.get_mark('attr_mark')
    print 'set visible', not event.in_
    mark.set_visible(not event.in_)
      

##############################
# Value Interface
##############################

  def popIfaceValue(self, acc):
    spinbutton = self.main_xml.get_widget('spinbutton_value')
    label_max = self.main_xml.get_widget('label_value_max')
    label_min = self.main_xml.get_widget('label_value_min')
    label_inc = self.main_xml.get_widget('label_value_inc')

    vi = pyLinAcc.Interfaces.IValue(acc)
     
    label_max.set_text(str(vi.maximumValue))
    label_min.set_text(str(vi.minimumValue))
    label_inc.set_text(str(vi.minimumIncrement))
    
    minimumIncrement = vi.minimumIncrement
    digits = 0

    while minimumIncrement - int(minimumIncrement) != 0:
      digits += 1
      minimumIncrement *= 10

    spinbutton.set_range(vi.minimumValue, vi.maximumValue)
     #spinbutton.set_increments(vi.minimumIncrement, vi.minimumIncrement)
    spinbutton.set_value(vi.currentValue)
    spinbutton.set_digits(digits)
  
  def _onValueSpinnerChange(self, widget):
     acc = self.acc
     try:
        vi = pyLinAcc.Interfaces.IValue(acc)
     except:
        return

     vi.currentValue = widget.get_value()


  def _accEventValue(self, event):
     if self.acc != event.source:
        return

     spinbutton = self.main_xml.get_widget('spinbutton_value')
     acc = self.acc
     try:
        vi = pyLinAcc.Interfaces.IValue(acc)
     except:
        return
     
     if spinbutton.get_value() != vi.currentValue:
        spinbutton.set_value(vi.currentValue)


  

