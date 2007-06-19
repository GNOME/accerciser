from accerciser.plugin import Plugin
from accerciser.i18n import N_, _
import gtk
import pyatspi
import wnck

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
                            gtk.keysyms.a,
                            gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK),
                           (N_('Inspect accessible under mouse'),
                            self._inspectUnderMouse, 
                            gtk.keysyms.question,
                            gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK)]

    pyatspi.Registry.registerEventListener(self._accEventFocusChanged, 
                                           'focus')

    self.last_focused = None

  def _accEventFocusChanged(self, event):
    '''
    Hold a reference for the last focused accessible. This is used when a certain 
    global hotkey is pressed to select this accessible.

    @param event: The event that is being handled.
    @type event: L{pyatspi.event.Event}
    '''
    if not self.isMyApp(event.source):
      self.last_focused = event.source      

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
    # Inspect accessible under mouse
    display = gtk.gdk.Display(gtk.gdk.get_display())
    screen, x, y, flags =  display.get_pointer()
    desktop = pyatspi.Registry.getDesktop(0)
    wnck_screen = wnck.screen_get_default()
    window_order = [w.get_name() for w in wnck_screen.get_windows_stacked()]
    top_window = (None, -1)
    for app in desktop:
      if not app or self.isMyApp(app):
        continue
      for frame in app:
        if not frame:
          continue
        acc = self._getChildAccAtCoords(frame, x, y)
        if acc:
          try:
            z_order = window_order.index(frame.name)
          except ValueError:
            continue
          if z_order > top_window[1]:
            top_window = (acc, z_order)
    if top_window[0]:
      self.node.update(top_window[0])

  def _getChildAccAtCoords(self, parent, x, y):
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
    container = parent
    while True:
      try:
        ci = container.queryComponent()
      except:
        return None
      else:
        inner_container = container
      container =  ci.getAccessibleAtPoint(x, y, pyatspi.DESKTOP_COORDS)
      if not container or container.queryComponent() == ci:
        # The gecko bridge simply has getAccessibleAtPoint return itself
        # if there are no further children
        break
    if inner_container == parent:
      return None
    else:
      return inner_container
