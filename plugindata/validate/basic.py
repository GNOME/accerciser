from accerciser.i18n import _
from pyatspi import *
from pyatspi.constants import *
from validate import Validator
import random

__metadata__ = {
  'name': _('Basic'),
  'description': _('Tests fundamental GUI application accessibility')}

URL_BASE = 'https://wiki.gnome.org/Apps/Accerciser/Validate#'


class ActionIsInteractive(Validator):
  '''
  Any item that supports the action interface should also be focusable or
  selectable so the user may interact with it via the keyboard.
  '''
  URL = URL_BASE + 'Actionable_ITEM_ROLE_is_not_focusable_or_selectable'

  def condition(self, acc):
    return acc.queryAction()

  def before(self, acc, state, view):
    s = acc.getState()
    if (not (s.contains(STATE_FOCUSABLE) or
             s.contains(STATE_SELECTABLE))):
      view.error(_('actionable %s is not focusable or selectable') %
                 acc.getLocalizedRoleName(), acc, self.URL)

class WidgetHasAction(Validator):
  '''
  Any widget with a role listed in condition should support the action
  interface.
  '''
  URL = URL_BASE + 'Interactive_ITEM_ROLE_is_not_actionable'
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
  '''
  The application should have on and only one accessible with state focused
  at any one time.
  '''
  URL = URL_BASE + 'More_than_one_focused_widget'
  def before(self, acc, state, view):
    s = acc.getState()
    if s.contains(STATE_FOCUSED):
      if 'focus' not in state:
        state['focus'] = acc
      else:
        view.error(_('more than one focused widget'), acc, self.URL)

class WidgetHasText(Validator):
  '''
  Any widget with a role listed in condition should support the text interface
  since they all support stylized text.
  '''
  URL = URL_BASE + 'ITEM_ROLE_has_no_text_interface'
  def condition(self, acc):
    return acc.getRole() in [
                             ROLE_TABLE_COLUMN_HEADER,
                             ROLE_TABLE_ROW_HEADER,
                             ROLE_PASSWORD_TEXT,
                             ROLE_TEXT, ROLE_ENTRY, ROLE_PARAGRAPH,
                             ROLE_LIST_ITEM,
                             ROLE_HEADING, ROLE_HEADER,
                             ROLE_FOOTER, ROLE_CAPTION,
                             ROLE_TERMINAL]

  def before(self, acc, state, view):
    try:
      acc.queryText()
    except NotImplementedError:
      view.error(_('%s has no text interface') % acc.getLocalizedRoleName(), acc, self.URL)

class ParentChildIndexMatch(Validator):
  '''
  The index returned by acc.getIndexInParent should return acc when provided
  to getChildAtIndex.
  '''
  URL = URL_BASE + 'ITEM_ROLE_index_in_parent_does_not_match_child_index'
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
                 acc.getLocalizedRoleName(), acc, self.URL)

class ReciprocalRelations(Validator):
  '''
  Any relation in the map should point to an accessible having the reciprocal
  relation.
  '''
  URL = URL_BASE + 'Missing_reciprocal_for_RELATION_NAME_relation'
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
      for i in range(rel.getNTargets()):
        if rel.getTarget(i) == acc:
          return True
    return False

  def before(self, acc, state, view):
    s = acc.getRelationSet()
    for rel in s:
      kind = rel.getRelationType()
      for i in range(rel.getNTargets()):
        target = rel.getTarget(i)
        ts = target.getRelationSet()
        rec = self._getReciprocal(kind)
        if not self._hasRelationTarget(ts, rec, acc):
          view.error(_('Missing reciprocal for %s relation') %
                     rel.getRelationTypeName(), acc, self.URL)

class HasLabelName(Validator):
  '''
  Any accessible with one of the roles listed below should have an accessible
  name, a labelled by relationship, or both.
  '''
  URL = URL_BASE + 'ITEM_ROLE_missing_name_or_label'
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
      for i in range(rel.getNTargets()):
        target = rel.getTarget(i)
        if self._checkForReadable(target):
          return
    # Translators: The first variable is the role name of the object that is missing
    # the name or label.
    #
    view.error(_('%s missing name or label') % acc.getLocalizedRoleName(), acc,
               self.URL)

class TableHasSelection(Validator):
  '''
  A focusable accessible with a table interface should also support the
  selection interface.
  '''
  URL = URL_BASE + \
    'Focusable_ITEM_ROLE_has_a_table_interface.2C_but_not_a_selection_interface'
  def condition(self, acc):
    acc.queryTable()
    return acc.getState().contains(STATE_FOCUSABLE)

  def before(self, acc, state, view):
    try:
      acc.querySelection()
    except NotImplementedError:
      view.error(_('focusable %s has a table interface, but not a selection interface') %
                 acc.getLocalizedRoleName(), acc, self.URL)

class StateWithAbility(Validator):
  '''
  Any accessible with one of the ephemeral states in state map should have the
  corresponding -able state.
  '''
  URL = URL_BASE + \
    'ITEM_ROLE_has_ITEM_EPHEMERAL_STATE_state_without_ITEM_ABLE_STATE_state'
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
      # Translators: First variable is an accessible role name, the next two
      # variables are accessible state names.
      # For example: "button has focused state without focusable state".
      #
      view.error(_('%s has %s state without %s state') % (
        acc.getLocalizedRoleName(),
        stateToString(self.test_state),
        stateToString(able_state)), acc, self.URL)

class RadioInSet(Validator):
  '''
  An accessible with a radio button role should be a member of a set as
  indicated by a relation or appropriate object property.
  '''
  URL = URL_BASE + 'ITEM_ROLE_does_not_belong_to_a_set'
  def condition(self, acc):
    return self.getRole() in [ROLE_RADIO_BUTTON, ROLE_RADIO_MENU_ITEM]

  def before(self, acc, state, view):
    attrs = acc.getAttributes()
    m = dict([attr.split(':', 1) for attr in attrs])
    if 'posinset' in m:
      return
    rels = acc.getRelationSet()
    for rel in rels:
      if rel.getRelationType() == RELATION_MEMBER_OF:
        return
    # Translators: The radio button does not belong to a set, thus it is useless.
    # The first variable is the object's role name.
    #
    view.error(_('%s does not belong to a set') % acc.getLocalizedRoleName(),
               acc, self.URL)

def _randomRowCol(table):
  rows, cols = table.nRows, table.nColumns
  r = random.randint(0, rows-1)
  c = random.randint(0, cols-1)
  return r, c

class TableRowColIndex(Validator):
  '''
  The index returned by getIndexAt(row, col) should result in getRowAtIndex
  and getColumnAtIndex returning the original row and col.
  '''
  URL = URL_BASE + 'ITEM_ROLEs_index_X_does_not_match_row_and_column'
  MAX_SAMPLES = 100
  def condition(self, acc):
    t = acc.queryTable()
    # must not be empty to test
    return (t.nRows and t.nColumns)

  def before(self, acc, state, view):
    t = acc.queryTable()
    samples = max(t.nRows * t.nColumns, self.MAX_SAMPLES)
    for i in range(samples):
      r, c = _randomRowCol(t)
      i = t.getIndexAt(r, c)
      ir = t.getRowAtIndex(i)
      ic = t.getColumnAtIndex(i)
      if r != ir or c != ic:
        # Translators: The row or column number retrieved from a table child's
        # object at a certain index is wrong.
        # The first variable is the role name of the object, the second is the
        # given index.
        #
        view.error(_('%(rolename)s index %(num)d does not match row and column') %
                   {'rolename':acc.getLocalizedRoleName(), 'num':i}, acc, self.URL)
        return

class TableRowColParentIndex(Validator):
  '''
  The accessible returned by table.getAccessibleAt should return
  acc.getIndexInParent matching acc.getIndexAt.
  '''
  URL = URL_BASE + \
    'ITEM_ROLEs_parent_index_X_does_not_match_row_and_column_index_Y'
  MAX_SAMPLES = 100
  def condition(self, acc):
    t = acc.queryTable()
    # must not be empty to test
    return (t.nRows and t.nColumns)

  def before(self, acc, state, view):
    t = acc.queryTable()
    samples = max(t.nRows * t.nColumns, self.MAX_SAMPLES)
    for i in range(samples):
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
        view.error(_('%(rolename)s parent index %(num1)d does not match row and column index %(num2)d') %
                   {'rolename':acc.getLocalizedRoleName(), 'num1':ip, 'num2':i}, acc, self.URL)
        return

class ImageHasName(Validator):
  '''
  Any accessible with an image role or image interface should have either a
  name, description, or image description.
  '''
  URL = URL_BASE + 'ITEM_ROLE_has_no_name_or_description'
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
                 acc.getLocalizedRoleName(), acc, self.URL)
