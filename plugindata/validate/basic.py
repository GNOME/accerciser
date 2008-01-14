from accerciser.i18n import _
from pyatspi import *
from pyatspi.constants import *
from validate import Validator
import random

__metadata__ = {
  'name': _('Basic'),
  'description': _('Tests fundamental GUI application accessibility')}

class ActionIsInteractive(Validator):
  URL = 'http://live.gnome.org/Accerciser/Validate#1'
  def condition(self, acc):
    return acc.queryAction()

  def before(self, acc, state, view):
    s = acc.getState()
    if (not (s.contains(STATE_FOCUSABLE) or
             s.contains(STATE_SELECTABLE))):
      view.error(_('actionable %s is not focusable or selectable') %
                 acc.getLocalizedRoleName(), acc, self.URL)

class WidgetHasAction(Validator):
  URL = 'http://live.gnome.org/Accerciser/Validate#2'
  def condition(self, acc):
    return acc.getRole() in [ROLE_PUSH_BUTTON, ROLE_MENU, ROLE_MENU_ITEM,
                             ROLE_CHECK_MENU_ITEM, ROLE_RADIO_MENU_ITEM,
                             ROLE_TOGGLE_BUTTON, ROLE_RADIO_BUTTON]

  def before(self, acc, state, view):
    try:
      acc.queryAction()
    except NotImplementedError:
      view.error(_('interactive %s is not actionable') %
                 acc.getLocalizedRoleName(), acc, self.URL)

class OneFocus(Validator):  
  def before(self, acc, state, view):
    s = acc.getState()
    if s.contains(STATE_FOCUSED):
      if not state.has_key('focus'):
        state['focus'] = acc
      else:
        view.error(_('more than one focused widget'), acc)

class WidgetHasText(Validator):
  def condition(self, acc):
    return acc.getRole() in [ROLE_PUSH_BUTTON, ROLE_MENU, ROLE_MENU_ITEM,
                             ROLE_CHECK_MENU_ITEM, ROLE_RADIO_MENU_ITEM,
                             ROLE_TOGGLE_BUTTON, ROLE_STATUS_BAR,
                             ROLE_TABLE_COLUMN_HEADER,
                             ROLE_TABLE_ROW_HEADER, ROLE_SPIN_BUTTON,
                             ROLE_SLIDER, ROLE_ROW_HEADER, ROLE_COLUMN_HEADER,
                             ROLE_RADIO_BUTTON, ROLE_PASSWORD_TEXT,
                             ROLE_TEXT, ROLE_ENTRY, ROLE_PARAGRAPH,
                             ROLE_PAGE_TAB, ROLE_LIST_ITEM, ROLE_LINK,
                             ROLE_HEADING, ROLE_HEADER,
                             ROLE_FOOTER, ROLE_CHECK_BOX, ROLE_CAPTION,
                             ROLE_TERMINAL]

  def before(self, acc, state, view):
    try:
      acc.queryText()
    except NotImplementedError:
      view.error(_('%s has no text interface') % acc.getLocalizedRoleName(), acc)

class ParentChildIndexMatch(Validator):
  def condition(self, acc):
    # don't test applications
    acc.queryApplication()
    return False
  
  def before(self, acc, state, view):
    pi = acc.getIndexInParent()
    child = acc.parent.getChildAtIndex(pi)
    if acc != child:
      # Translators: The first variable is the role name of the object that has an
      # index mismatch.
      # 
      view.error(_('%s index in parent does not match child index') %
                 acc.getLocalizedRoleName(), acc)

class ReciprocalRelations(Validator):
  REL_MAP = {RELATION_LABEL_FOR : RELATION_LABELLED_BY,
             RELATION_CONTROLLER_FOR : RELATION_CONTROLLED_BY,
             RELATION_MEMBER_OF : RELATION_MEMBER_OF,
             RELATION_FLOWS_TO : RELATION_FLOWS_FROM,
             RELATION_EMBEDS : RELATION_EMBEDDED_BY,
             RELATION_POPUP_FOR : RELATION_PARENT_WINDOW_OF,
             RELATION_DESCRIPTION_FOR : RELATION_DESCRIBED_BY}
  
  def condition(self, acc):
    s = acc.getRelationSet()
    return len(s) > 0

  def _getReciprocal(self, kind):
    return self.REL_MAP.get(kind)

  def _hasRelationTarget(self, s, kind, acc):
    if kind is None:
      return True
    
    for rel in s:
      rec = rel.getRelationType()
      if kind != rec:
        continue
      for i in xrange(rel.getNTargets()):
        if rel.getTarget(i) == acc:
          return True
    return False

  def before(self, acc, state, view):
    s = acc.getRelationSet()
    for rel in s:
      kind = rel.getRelationType()
      for i in xrange(rel.getNTargets()):
        target = rel.getTarget(i)
        ts = target.getRelationSet()
        rec = self._getReciprocal(kind)
        if not self._hasRelationTarget(ts, rec, acc):
          view.error(_('Missing reciprocal for %s relation') %
                     rel.getRelationTypeName(), acc)
    
class HasLabelName(Validator):
  URL = 'http://live.gnome.org/Accerciser/Validate#4'
  TEXT_CANNOT_LABEL = [ROLE_SPIN_BUTTON, ROLE_SLIDER, ROLE_PASSWORD_TEXT,
                       ROLE_TEXT, ROLE_ENTRY, ROLE_TERMINAL]
                   
  TEXT_CAN_LABEL = [ROLE_PUSH_BUTTON, ROLE_MENU, ROLE_MENU_ITEM,
                    ROLE_CHECK_MENU_ITEM, ROLE_RADIO_MENU_ITEM,
                    ROLE_TOGGLE_BUTTON, ROLE_TABLE_COLUMN_HEADER,
                    ROLE_TABLE_ROW_HEADER, ROLE_ROW_HEADER,
                    ROLE_COLUMN_HEADER, ROLE_RADIO_BUTTON, ROLE_PAGE_TAB,
                    ROLE_LIST_ITEM, ROLE_LINK, ROLE_LABEL, ROLE_HEADING,
                    ROLE_HEADER, ROLE_FOOTER, ROLE_CHECK_BOX, ROLE_CAPTION,
                    ]

  def condition(self, acc):
    return acc.getRole() in (self.TEXT_CANNOT_LABEL + self.TEXT_CAN_LABEL)

  def _checkForReadable(self, acc):
    if acc.name and acc.name.strip():
      return True
    if acc in self.TEXT_CAN_LABEL:
      try:
        t = acc.queryText()
      except NotImplementedError:
        return False
      if t.getText(0, -1).strip():
        return True
    return False

  def before(self, acc, state, view):
    if self._checkForReadable(acc):
      return
    for rel in acc.getRelationSet():
      if rel.getRelationType() != RELATION_LABELLED_BY:
        continue
      for i in xrange(rel.getNTargets()):
        target = rel.getTarget(i)
        if self._checkForReadable(target):
          return
    # Translators: The first variable is the role name of the object that is missing
    # the name or label.
    # 
    view.error(_('%s missing name or label') % acc.getLocalizedRoleName(), acc,
               self.URL)
    
class TableHasSelection(Validator):
  def condition(self, acc):
    acc.queryTable()
    return acc.getState().contains(STATE_FOCUSABLE)

  def before(self, acc, state, view):
    try:
      acc.querySelection()
    except NotImplementedError:
      view.error(_('focusable %s has table interface, no selection interface') %
                 acc.getLocalizedRoleName(), acc)
                 
class StateWithAbility(Validator):
  STATE_MAP = {STATE_EXPANDED : STATE_EXPANDABLE,
               STATE_COLLAPSED : STATE_EXPANDABLE,
               STATE_FOCUSED : STATE_FOCUSABLE,
               STATE_SELECTED: STATE_SELECTABLE}
  def condition(self, acc):
    ss = acc.getState()
    for s in self.STATE_MAP:
      if ss.contains(s):
        self.test_state = s
        return True

  def before(self, acc, state, view):
    ss = acc.getState()
    able_state = self.STATE_MAP[self.test_state]
    if not ss.contains(able_state):
      view.error(_('%s has %s state without %s state') % (
        acc.getLocalizedRoleName(),
        stateToString(self.test_state),
        stateToString(able_state)), acc)

class RadioInSet(Validator):
  def condition(self, acc):
    return self.getRole() in [ROLE_RADIO_BUTTON, ROLE_RADIO_MENU_ITEM]

  def before(self, acc, state, view):
    attrs = acc.getAttributes()
    m = dict([attr.split(':', 1) for attr in attrs])
    if m.has_key('posinset'):
      return
    rels = acc.getRelationSet()
    for rel in rels:
      if rel.getRelationType() == RELATION_MEMBER_OF:
        return
    # Translators: The radio button does not belong to a set, thus it is useless.
    # The first variable is the object's role name.
    # 
    view.error(_('%s does not belong to a set') % acc.getLocalizedRoleName(),
               acc)

def _randomRowCol(table):
  rows, cols = table.nRows, table.nColumns
  r = random.randint(0, rows-1)
  c = random.randint(0, cols-1)
  return r, c
    
class TableRowColIndex(Validator):
  MAX_SAMPLES = 100
  def condition(self, acc):
    t = acc.queryTable()
    # must not be empty to test
    return (t.nRows and t.nColumns)

  def before(self, acc, state, view):
    t = acc.queryTable()
    samples = max(t.nRows * t.nColumns, self.MAX_SAMPLES)
    for i in xrange(samples):
      r, c = _randomRowCol(t)
      i = t.getIndexAt(r, c)
      ir = t.getRowAtIndex(i)
      ic = t.getColumnAtIndex(i)
      if r != ir or c != ic:
        # Translators: The row or column number retrieved from a table child's object
        # at a certain index is wrong.
        # The first variable is the role name of the object, the second is the
        # given index.
        # 
        view.error(_('%s index %d does not match row and column') %
                   (acc.getLocalizedRoleName(), i), acc)
        return

class TableRowColParentIndex(Validator):
  MAX_SAMPLES = 100
  def condition(self, acc):
    t = acc.queryTable()
    # must not be empty to test
    return (t.nRows and t.nColumns)

  def before(self, acc, state, view):
    t = acc.queryTable()
    samples = max(t.nRows * t.nColumns, self.MAX_SAMPLES)
    for i in xrange(samples):
      r, c = _randomRowCol(t)
      child = t.getAccessibleAt(r, c)
      ip = child.getIndexInParent()
      i = t.getIndexAt(r, c)
      if i != ip:
        # Translators: The "parent index" is the order of the child in the parent.
        # the "row and column index" should be the same value retrieved by the
        # object's location in the table.
        # The first variable is the object's role name, the second and third variables
        # are index numbers.
        #
        view.error(_('%s parent index %d does not match row and column index %d') %
                   (acc.getLocalizedRoleName(), ip, i), acc)
        return

class ImageHasName(Validator):
  def condition(self, acc):
    if acc.getRole() in [ROLE_DESKTOP_ICON, ROLE_ICON, ROLE_ANIMATION,
                         ROLE_IMAGE]:
      return True
    acc.queryImage()
    return True

  def before(self, acc, state, view):
    if ((acc.name and acc.name.strip()) or
        (acc.description and acc.description.strip())):
      return
    ni = False
    try:
      im = acc.queryImage()
    except NotImplementedError:
      ni = True
    if ni or im.imageDescription is None or not im.imageDescription.strip():
      view.error(_('%s has no name or description') % 
                 acc.getLocalizedRoleName(), acc)
