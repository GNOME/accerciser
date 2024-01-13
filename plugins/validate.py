'''
AT-SPI validation plugin.

@author: Peter Parente
@organization: IBM Corporation
@copyright: Copyright (c) 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''
import gi

from gi.repository import Gtk as gtk
from gi.repository import GObject
from gi.repository import GLib

import os
import traceback
import sys
import glob
import importlib
import webbrowser
from accerciser.plugin import ViewportPlugin
from accerciser.i18n import _, N_, DOMAIN
import pyatspi

UI_FILE = os.path.join(os.path.dirname(__file__), 'validate.ui')
USER_SCHEMA_PATH = os.path.join(GLib.get_user_data_dir(), 'accerciser',
                                'plugindata', 'validate')
SYS_SCHEMA_PATH = os.path.join(sys.prefix, 'share', 'accerciser',
                               'plugindata', 'validate')
VALIDATORS = {}
SCHEMA_METADATA = {}

# method to make use of metaclasses on both python 2.x and 3.x
#
def with_metaclass(meta, *bases):
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__
        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)
    return metaclass('temporary_class', None, {})

class ValidatorManager(type):
  '''
  Metaclass that tracks all validator subclasses imported by the plug-in.
  Used to update a list of validator schemas at runtime.
  '''
  def __init__(cls, name, bases, dct):
    '''
    Build the class as usual, but keep track of its name and one instance.
    '''
    super(ValidatorManager, cls).__init__(name, bases, dct)
    if name != 'Validator':
      # don't count the base class
      names = cls.__module__.split('.')
      VALIDATORS.setdefault(names[-1], []).append(cls())

  @staticmethod
  def loadSchemas():
    '''
    Loads all schema files from well known locations.
    '''
    for path in [USER_SCHEMA_PATH, SYS_SCHEMA_PATH]:
      for fn in glob.glob(os.path.join(path, '*.py')):
        module_name = os.path.basename(fn)[:-3]
        spec = importlib.util.spec_from_file_location(module_name, fn)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        try:
          # try to get descriptive fields from the module
          SCHEMA_METADATA[module_name] = module.__metadata__
        except AttributeError:
          # default to usinf file name as description
          SCHEMA_METADATA[module_name] = {'name' : module,
                                          'description' : _('No description')}

  @staticmethod
  def getValidators(name):
    '''
    Gets all validator classes within a schema.

    @param name: Name of a schema
    @return: List of Validator objects
    @raise KeyError: When the schema is not known
    '''
    return VALIDATORS[name]

  @staticmethod
  def listSchemas():
    '''
    Gets a list of all available schema names.

    @return: List of string names
    '''
    return list(VALIDATORS.keys())

  @staticmethod
  def getSchemaMetadata(name):
    '''
    Gets information about a schema.

    @param name: Name of the schema
    @return: Dictionary of 'name', 'description', etc.
    '''
    return SCHEMA_METADATA[name]

class Validator(with_metaclass(ValidatorManager, object)):
  '''
  Base class for all validators. Defines the public interface used by the
  plug-in controller/view to generate validation reports.
  '''
  def __init__(self):
    pass

  def condition(self, acc):
    '''
    Checks if this validator is fit to test the given accessible. For instance,
    a test for table properties is not applicable to buttons.

    @param acc: Accessible to test
    @return: True to validate, False to avoid testing
    @raise Exception: Same as returning False
    '''
    return True

  def before(self, acc, state, view):
    '''
    Tests the accessible before testing its descendants.

    @param acc: Accessible to test
    @param state: Dictionary containing arbitrary state that will be passed
      among validators and be made available in both before and after passes
    @param view: View object to use to log test results
    '''
    pass

  def after(self, acc, state, view):
    '''
    Tests the accessible after testing its descendants.

    @param acc: Accessible to test
    @param state: Dictionary containing arbitrary state that will be passed
      among validators and be made available in both before and after passes
    @param view: View object to use to log test results
    '''
    pass

class ValidatorViewport(ViewportPlugin):
  '''
  Validator UI. Key feature is a table showing the results of a validation
  run on some accessible and its descendants.

  @ivar main_xml: gtk builder parsed XML definition
  @ivar report: Report table
  @ivar progress: Activity bar
  @ivar validate: Validation button
  @ivar save: Save report button
  @ivar schema: Schema combobox
  @ivar vals: All validators for the selected schema
  @ivar walk: Generator for the current validation walk through the hierarchy
  '''
  plugin_name = N_('AT-SPI Validator')
  plugin_name_localized = _(plugin_name)
  plugin_description = N_('Validates application accessibility')

  # keep track of when a file is being written
  write_in_progress = False

  def init(self):
    '''
    Loads the glade UI definition and initializes it.
    '''
    # load all schemas
    ValidatorManager.loadSchemas()

    # validators and walk generator
    self.vals = None
    self.walk = None
    # help url for last selected
    self.url = None

    self.main_xml = gtk.Builder()
    self.main_xml.set_translation_domain(DOMAIN)
    self.main_xml.add_from_file(UI_FILE)
    frame = self.main_xml.get_object('main vbox')
    self.plugin_area.add(frame)
    self.report = self.main_xml.get_object('report table')
    self.progress = self.main_xml.get_object('progress bar')
    self.validate = self.main_xml.get_object('validate button')
    self.help = self.main_xml.get_object('help button')
    self.save = self.main_xml.get_object('save button')
    self.clear = self.main_xml.get_object('clear button')
    self.schema = self.main_xml.get_object('schema combo')
    self.validator_buffer = gtk.TextBuffer()
    self.idle_validate_id = None

    # model for the combobox
    model = gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
    self.schema.set_model(model)

    # append all schema names/descriptions
    vm = ValidatorManager
    for name in vm.listSchemas():
      d = vm.getSchemaMetadata(name)
      model.append(['%s - %s' % (d['name'], d['description']), name])
    self.schema.set_active(0)

    # model for the report
    model = gtk.ListStore(str, str, object, str)
    self.report.set_model(model)

    # schema cell renderer
    cell = gtk.CellRendererText()
    self.schema.pack_start(cell, True)
    self.schema.add_attribute(cell, 'text', 0)

    # log level column
    col = gtk.TreeViewColumn(_('Level'))
    rend = gtk.CellRendererText()
    col.pack_start(rend, True)
    col.add_attribute(rend, 'text', 0)
    self.report.append_column(col)
    # description column
    rend = gtk.CellRendererText()
    col = gtk.TreeViewColumn(_('Description'), rend, text=1)
    self.report.append_column(col)

    # set progress bar to zero initially
    self.progress.set_fraction(0.0)

    self.main_xml.connect_signals(self)
    self.show_all()

  def onAccChanged(self, acc):
    '''
    Stops validation if the accessible hierarchy changes.

    @param acc: The accessible that changed
    '''
    if self.walk is not None:
      self._stopValidate()

  def _onValidate(self, widget):
    '''
    Starts or stops a validation run.

    @param widget: The validate button
    '''
    if widget.get_active():
      self._startValidate()
    else:
      self._stopValidate()

  def _writeFile(self):
    '''
    Save the report from the report model to disk in a temporary location.
    Close the file when finished.
    '''
    if self.write_in_progress:
      # if we have finished writing to the file
      if self.curr_file_row == self.n_report_rows:
        self.save_to.close()
        self._stopSave()
        return False
    else:
      # set up the file to be written
      self._startSave()
      self.save.set_sensitive(False)
      report_store = self.report.get_model()
      # create list of lists containing column values
      self.row_values = [[row[0], row[1], row[2], row[3]] for row in report_store]
      self.n_report_rows = len(self.row_values)
      return True

    remaining_rows = self.n_report_rows - self.curr_file_row
    n_rows_to_write = 5
    if n_rows_to_write > remaining_rows:
      n_rows_to_write = remaining_rows

    file_str_list = [] # list to store strings to be written to file
    start = self.curr_file_row
    end = (self.curr_file_row + n_rows_to_write)
    for i in range(start, end):
      val = self.row_values[i]
      # add level to buffer
      file_str_list.append("%s: %s\n" % (_('Level'), val[0]))
      # add description to buffer
      file_str_list.append("%s: %s\n" % (_('Description'), val[1]))
      # add accessible's name to buffer
      file_str_list.append("%s: %s\n" % (_('Name'), val[2].name))
      # add accessible's role to buffer
      file_str_list.append("%s: %s\n" % (_('Role'), val[2].getRoleName()))
      # add url role to buffer
      file_str_list.append("%s: %s\n\n" % (_('Hyperlink'), val[3]))
      self.curr_file_row += 1

    self.save_to.write(''.join(file_str_list))

    return True

  def _onSave(self, button):
    '''
    Save the report from the report model to disk

    @param button: Save button
    '''
    save_dialog = gtk.FileChooserNative.new(
      _('Save validator output'),
      self.get_toplevel(),
      gtk.FileChooserAction.SAVE,
      _('_OK'),
      _('_Cancel'))
    save_dialog.set_do_overwrite_confirmation(True)
    response = save_dialog.run()
    if response == gtk.ResponseType.ACCEPT:
      self.save_to = open(save_dialog.get_filename(), 'w')
      GLib.idle_add(self._writeFile)
    save_dialog.destroy()

  def _onClear(self, button):
    '''
    Clear the report from the report model

    @param button: Clear button
    '''
    self.report.get_model().clear()
    self.validator_buffer.set_text('')
    self.save.set_sensitive(False)
    self.clear.set_sensitive(False)

  def _onHelp(self, button):
    '''
    Open a help URL in the system web browser.

    @param button: Help button
    '''
    webbrowser.open(self.url)

  def _onSaveIdle(self):
    '''
    Move the progress bar
    '''
    self.progress.pulse()
    return True

  def _startSave(self):
    '''
    Starts a save by settting up an idle callback after initializing progress
    bar.
    '''
    # set variables for writing report to file
    self.write_in_progress = True
    self._setDefaultSaveVars()
    # register an idle callback
    self.idle_save_id = GLib.idle_add(self._onSaveIdle)
    self.progress.set_text(_('Saving'))
    # disable controls
    self.validate.set_sensitive(False)
    self.save.set_sensitive(False)

  def _stopSave(self):
    '''
    Stops a save by disabling the idle callback and restoring the various UI
    components to their enabled states.
    '''
    # stop callbacks
    GLib.source_remove(self.idle_save_id)
    # reset progress
    self.progress.set_fraction(0.0)
    self.progress.set_text(_('Idle'))
    # enable other controls
    self.validate.set_sensitive(True)
    self.save.set_sensitive(True)
    self.save.set_sensitive(True)
    # reset variables for writing report to file
    self._setDefaultSaveVars()
    self.write_in_progress = False

  def _setDefaultSaveVars(self):
    '''
    Ready appropriate variables for a save
    '''
    self.curr_file_row = 0
    self.n_report_rows = 0
    self.row_values = []

  def _startValidate(self):
    '''
    Starts a validation by settting up an idle callback after initializing the
    report table and progress bar. Gets all validators for the selected schema.
    '''
    # clear the report
    self.report.get_model().clear()
    # get the validators
    index = self.schema.get_active()
    if index == -1:
      self.validate.set_active(False)
      return
    row = self.schema.get_model()[index]
    self.vals = ValidatorManager.getValidators(row[1])
    # build a new state dict
    state = {}
    # build our walk generator
    self.walk = self._traverse(self.acc, state)
    # register an idle callback
    self.idle_validate_id = GLib.idle_add(self._onValidateIdle)
    self.progress.set_text(_('Validating'))
    # disable controls
    self.schema.set_sensitive(False)
    self.help.set_sensitive(False)
    self.save.set_sensitive(False)
    self.clear.set_sensitive(False)

  def _stopValidate(self):
    '''
    Stops a validation run by disabling the idle callback and restoring the
    various UI components to their enabled states.
    '''
    if self.idle_validate_id == None:
      return
    # stop callbacks
    GLib.source_remove(self.idle_validate_id)
    # destroy generator
    self.walk = None
    # reset progress
    self.progress.set_fraction(0.0)
    self.progress.set_text(_('Idle'))
    # depress validate
    self.validate.set_active(False)
    # enable other controls
    self.schema.set_sensitive(True)
    self.help.set_sensitive(True)
    self.save.set_sensitive(True)
    self.clear.set_sensitive(True)

  def _onValidateIdle(self):
    '''
    Tests one accessible at a time on each idle callback by advancing the
    walk generator.
    '''
    try:
      # generate the next accessible to validate
      next(self.walk)
    except StopIteration:
      # nothing left to validate, so stop
      self._stopValidate()
      return False
    # pule the progress bar
    self.progress.pulse()
    # yes, we want more callbacks
    return True

  def _traverse(self, acc, state):
    '''
    Generates accessibles in a two-pass traversal of the subtree rooted at
    the accessible selected at the time the validation starts. Accessibles are
    tested first before their descendants (before pass) and then after all of
    their descendants (after pass).

    @param acc: Accessible root of some subtree in the walk
    @param state: State object used by validators to share information
    '''
    # start the walk generator
    gen_child = self._genAccessible(acc, state)
    while 1:
      try:
        # get one child
        child = next(gen_child)
      except StopIteration as e:
        break
      # recurse
      gen_traverse = self._traverse(child, state)
      while 1:
        # yield before continuing processing
        yield None
        try:
          # get one descendant
          next(gen_traverse)
        except StopIteration:
          break

  def _genAccessible(self, acc, state):
    '''
    Tests the given accessible in the before pass if its test condition is
    satisfied. Then generates all of its children. Finally, tests the original
    accessible in the after pass if its test condition is satisfied.

    @param acc: Accessible to test
    @param state: State object used by validators to share information
    '''
    # run before() methods on all validators
    self._runValidators(acc, state, True)
    # generate all children, but only if acc doesn't manage descendants
    if not acc.getState().contains(pyatspi.constants.STATE_MANAGES_DESCENDANTS):
      for i in range(acc.childCount):
        child = acc.getChildAtIndex(i)
        yield child
    # run after methods on all validators
    self._runValidators(acc, state, False)

  def _runValidators(self, acc, state, before):
    '''
    Runs all validators on a single accessible. If the validator condition is
    true, either executes the before() or after() method on the validator
    depending on the param 'before' passed to this method.

    @param acc: Accessible to test
    @param state: State object used by validators to share information
    @param before: True to execute before method, false to execute after
    '''
    for val in self.vals:
      try:
        ok = val.condition(acc)
      except Exception:
        pass
      else:
        if ok:
          try:
            if before:
              val.before(acc, state, self)
            else:
              val.after(acc, state, self)
          except Exception as e:
            self._exceptionError(acc, e)

  def _onCursorChanged(self, report):
    '''
    Enables or disables the help button based on whether an item has help or
    not.

    @param report: Report table
    '''
    selection = report.get_selection()
    model, iter = selection.get_selected()
    if iter:
      url = model[iter][3]
      self.help.set_sensitive(len(url))
      self.url = url

  def _onActivateRow(self, report, iter, col):
    '''
    Updates the Accerciser tree to show an accessible when a report entry is
    selected.

    @param report: Report table
    @param iter: Tree table iterator
    @param col: Tree table column
    '''
    selection = report.get_selection()
    model, iter = selection.get_selected()
    if iter:
      acc = model[iter][2]
      if acc:
        self.node.update(acc)

  def _exceptionError(self, acc, ex):
    '''
    Logs an unexpected exception that occurred during execution of a validator.

    @param acc: Accessible under test when the exception occurred
    @param ex: The exception
    '''
    info = traceback.extract_tb(sys.exc_info()[2])
    text = '%s (%d): %s' % (os.path.basename(info[-1][0]), info[-1][1], ex)
    self.report.get_model().append([_('EXCEPT'), text, acc, ''])

  def error(self, text, acc, url=''):
    '''
    Used by validators to log messages for accessibility problems that have to
    be fixed.
    '''
    level = _('ERROR')
    self.report.get_model().append([level, text, acc, url])

  def warn(self, text, acc, url=''):
    '''
    Used by validators to log warning messages for accessibility problems that
    should be fixed, but are not critical.
    '''
    level = _('WARN')
    self.report.get_model().append([level, text, acc, url])

  def info(self, text, acc, url=''):
    '''
    Used by validators to log informational messages.
    '''
    level = _('INFO')
    self.report.get_model().append([level, text, acc, url])

  def debug(self, text, acc, url=''):
    '''
    Used by validators to log debug messages.
    '''
    level = _('DEBUG')
    self.report.get_model().append([level, text, acc, url])

  def close(self):
    '''
    Things to do before the plugin closes.
    '''
    # don't close the plugin until we have finished writing
    while True:
      if not self.write_in_progress:
        break
      gtk.main_iteration_do(True)


