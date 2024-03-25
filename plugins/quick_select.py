import gi

from gi.repository import Gdk as gdk

from accerciser.plugin import Plugin
from accerciser.i18n import N_, _
from accerciser import window_manager

import pyatspi

class QuickSelect(Plugin):
  '''
  Plugin class for quick select.
  '''
  plugin_name = N_('Quick Select')
  plugin_name_localized = _(plugin_name)
  plugin_description = \
      N_('Plugin with various methods of selecting accessibles quickly.')

  def init(self):
    '''
    Initialize plugin.
    '''
    self.global_hotkeys = [(N_('Inspect last focused accessible'),
                            self._inspectLastFocused,
                            gdk.KEY_a, gdk.ModifierType.CONTROL_MASK | \
                                       gdk.ModifierType.MOD1_MASK),
                           (N_('Inspect accessible under mouse'),
                            self._inspectUnderMouse,
                            gdk.KEY_question, gdk.ModifierType.CONTROL_MASK | \
                                              gdk.ModifierType.MOD1_MASK)]

    pyatspi.Registry.registerEventListener(self._accEventFocusChanged,
                               'object:state-changed')

    pyatspi.Registry.registerEventListener(self._accEventSelectionChanged,
                               'object:selection-changed')

    self.last_focused = None
    self.last_selected = None
    self.window_manager = window_manager.get_window_manager()

  def _accEventFocusChanged(self, event):
    '''
    Hold a reference for the last focused accessible. This is used when a certain
    global hotkey is pressed to select this accessible.

    @param event: The event that is being handled.
    @type event: L{pyatspi.event.Event}
    '''
    if event.type != "object:state-changed:focused" and \
       event.type != "object:state-changed:selected":
      return

    if event.detail1 != 1:
      return

    if not self.isMyApp(event.source):
      self.last_focused = event.source

  def _accEventSelectionChanged(self, event):
    '''
    Hold a reference for the last parent of a selected accessible.
    This will be useful if we want to find an accessible at certain coords.

    @param event: The event that is being handled.
    @type event: L{pyatspi.event.Event}
    '''
    if not self.isMyApp(event.source):
      self.last_selected = event.source

  def _inspectLastFocused(self):
    '''
    Inspect the last focused widget's accessible.
    '''
    if self.last_focused:
      self.node.update(self.last_focused)

  def _inspectUnderMouse(self):
    '''
    Inspect accessible of widget under mouse.
    '''
    x, y = self.window_manager.getMousePosition()

    # First check if the currently selected accessible has the pointer over it.
    # This is an optimization: Instead of searching for
    # STATE_SELECTED and ROLE_MENU and LAYER_POPUP in the entire tree.
    item = self._getPopupItem(x, y)
    if item:
      self.node.update(item)
      return

    # Inspect accessible under mouse
    window_order = self.window_manager.getCurrentWorkspaceWindowOrder()
    top_window = (None, -1)
    desktop = pyatspi.Registry.getDesktop(0)
    for app in desktop:
      if not app or self.isMyApp(app):
        continue
      for frame in app:
        if not frame:
          continue
        acc = self._getComponentAtCoords(frame, x, y)
        if acc:
          try:
            z_order = window_order.index(frame.name)
          except ValueError:
            # It's possibly a popup menu, so it would not be in our frame name
            # list. And if it is, it is probably the top-most component.
            try:
              if acc.queryComponent().getLayer() == pyatspi.LAYER_POPUP:
                self.node.update(acc)
                return
            except:
              pass
          else:
            if z_order > top_window[1]:
              top_window = (acc, z_order)

    if top_window[0]:
      self.node.update(top_window[0])

  def _getPopupItem(self, x, y):
    suspect_children = []
    # First check if the currently selected accessible has the pointer over it.
    # This is an optimization: Instead of searching for
    # STATE_SELECTED and ROLE_MENU and LAYER_POPUP in the entire tree.
    if self.last_selected and \
          self.last_selected.getRole() == pyatspi.ROLE_MENU and \
          self.last_selected.getState().contains(pyatspi.STATE_SELECTED):
      try:
        si = self.last_selected.querySelection()
      except NotImplementedError:
        return None

      if si.nSelectedChildren > 0:
        suspect_children = [si.getSelectedChild(0)]
      else:
        suspect_children = self.last_selected

      if self.window_manager.supportsScreenCoords(self.last_selected):
        coord_type = pyatspi.DESKTOP_COORDS
      else:
        coord_type = pyatspi.WINDOW_COORDS
        x, y = self.window_manager.convertScreenToWindowCoords(x, y, self.last_selected)

      for child in suspect_children:
        try:
          ci = child.queryComponent()
        except NotImplementedError:
          continue

        if ci.contains(x, y, coord_type) and \
              ci.getLayer() == pyatspi.LAYER_POPUP:
          return child

      return None

  def _getComponentAtCoords(self, parent, x, y):
    '''
    Gets any child accessible that resides under given desktop coordinates.

    @param parent: Top-level accessible.
    @type parent: L{Accessibility.Accessible}
    @param x: X coordinate.
    @type x: integer
    @param y: Y coordinate.
    @type y: integer

    @return: Child accessible at given coordinates, or None.
    @rtype: L{Accessibility.Accessible}
    '''
    if self.window_manager.supportsScreenCoords(parent):
      coord_type = pyatspi.DESKTOP_COORDS
    else:
      coord_type = pyatspi.WINDOW_COORDS
      x, y = self.window_manager.convertScreenToWindowCoords(x, y, parent)

    container = parent
    inner_container = None
    while True:
      container_role = container.getRole()
      if container_role == pyatspi.ROLE_PAGE_TAB_LIST:
        try:
          si = container.querySelection()
          container = si.getSelectedChild(0)[0]
        except NotImplementedError:
          pass
      try:
        ci = container.queryComponent()
      except:
        break
      else:
        inner_container = container
      container =  ci.getAccessibleAtPoint(x, y, coord_type)
      if not container or container.queryComponent() == ci:
        # The gecko bridge simply has getAccessibleAtPoint return itself
        # if there are no further children
        break
    if inner_container == parent:
      return None
    else:
      return inner_container

