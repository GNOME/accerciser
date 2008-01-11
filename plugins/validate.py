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
import gtk
import gobject
import os
import traceback
import sys
import glob
import imp
import webbrowser
from accerciser.plugin import ViewportPlugin
from accerciser.i18n import _, N_
import pyatspi

GLADE_FILE = os.path.join(os.path.dirname(__file__), 'validate.glade')
USER_SCHEMA_PATH = os.path.join(os.environ['HOME'], '.accerciser', 
                                'plugindata', 'validate')
SYS_SCHEMA_PATH = os.path.join(sys.prefix, 'accerciser', 
                               'plugindata', 'validate')
VALIDATORS = {}
SCHEMA_METADATA = {}

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
        module = os.path.basename(fn)[:-3]
        params = imp.find_module(module, [path])
        schema = imp.load_module(module, *params)
        try:
          # try to get descriptive fields from the module
          SCHEMA_METADATA[module] = schema.__metadata__
        except AttributeError:
          # default to usinf file name as description
          SCHEMA_METADATA[module] = {'name' : module,
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
    return VALIDATORS.keys()

  @staticmethod
  def getSchemaMetadata(name):
    '''
    Gets information about a schema.

    @param name: Name of the schema
    @return: Dictionary of 'name', 'description', etc.
    '''
    return SCHEMA_METADATA[name]

class Validator(object):
  '''
  Base class for all validators. Defines the public interface used by the 
  plug-in controller/view to generate validation reports.
  '''
  __metaclass__ = ValidatorManager
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

  @ivar main_xml: glade parsed XML definition
  @ivar report: Report table
  @ivar progress: Activity bar
  @ivar validate: Validation button
  @ivar save: Save report button
  @ivar schema: Schema combobox
  @ivar vals: All validators for the selected schema
  @ivar walk: Generator for the current validation walk through the hierarchy
  '''
  plugin_name = N_('AT-SPI Validator')
  plugin_description = N_('Validates application accessibility')
  
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

    self.main_xml = gtk.glade.XML(GLADE_FILE, 'main vbox')
    frame = self.main_xml.get_widget('main vbox')
    self.plugin_area.add(frame)
    self.report = self.main_xml.get_widget('report table')
    self.progress = self.main_xml.get_widget('progress bar')
    self.validate = self.main_xml.get_widget('validate button')
    self.save = self.main_xml.get_widget('save button')
    self.help = self.main_xml.get_widget('help button')
    self.schema = self.main_xml.get_widget('schema combo')

    # model for the combobox
    model = gtk.ListStore(gobject.TYPE_STRING)
    self.schema.set_model(model)

    # append all schema names/descriptions
    vm = ValidatorManager
    for d in [vm.getSchemaMetadata(name) for name in vm.listSchemas()]:
      model.append(['%s - %s' % (d['name'], d['description'])])
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
    col.set_attributes(rend, text=0)
    self.report.append_column(col)
    # description column
    rend = gtk.CellRendererText()
    col = gtk.TreeViewColumn(_('Description'), rend, text=1)
    self.report.append_column(col)

    # set progress bar to zero initially
    self.progress.set_fraction(0.0)
        
    self.main_xml.signal_autoconnect(self)
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

  def _onSaveAs(self, button):
    pass

  def _onHelp(self, button):
    '''
    Open a help URL in the system web browser.

    @param button: Help button
    '''
    webbrowser.open(self.url)

  def _startValidate(self):
    '''
    Starts a validation by settting up an idle callback after initializing the
    report table and progress bar. Gets all validators for the selected schema.
    '''
    # clear the report
    self.report.get_model().clear()
    # get the validators
    self.vals = ValidatorManager.getValidators('basic')
    # build a new state dict
    state = {}
    # build our walk generator
    self.walk = self._traverse(self.acc, state)
    # register an idle callback
    self.idle_id = gobject.idle_add(self._onIdle)
    self.progress.set_text(_('Validating'))
    # disable controls
    self.schema.set_sensitive(False)
    self.save.set_sensitive(False)
    self.help.set_sensitive(False)

  def _stopValidate(self):
    '''
    Stops a validation run by disabling the idle callback and restoring the
    various UI components to their enabled states.
    '''
    # stop callbacks
    gobject.source_remove(self.idle_id)
    # destroy generator
    self.walk = None
    # reset progress
    self.progress.set_fraction(0.0)
    self.progress.set_text(_('Idle'))
    # depress validate
    self.validate.set_active(False)
    # enable other controls
    self.schema.set_sensitive(True)
    self.save.set_sensitive(True)
     
  def _onIdle(self):
    '''
    Tests one accessible at a time on each idle callback by advancing the
    walk generator.
    '''
    try:
      # generate the next accessible to validate
      self.walk.next()
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
        child = gen_child.next()
      except StopIteration, e:
        break
      # recurse
      gen_traverse = self._traverse(child, state)
      while 1:
        # yield before continuing processing 
        yield None
        try:
          # get one descendant
          gen_traverse.next()
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
      for i in xrange(acc.childCount):
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
          except Exception, e:
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
    self.report.get_model().append([_('EXCEPT'), text, acc])
    
  def error(self, text, acc, url=''):
    '''
    Used by validators to log messages for accessibility problems that have to
    be fixed.
    '''
    self.report.get_model().append([_('ERROR'), text, acc, url])
    
  def warn(self, text, acc, url=''):
    '''
    Used by validators to log warning messages for accessibility problems that
    should be fixed, but are not critical.
    '''
    self.report.get_model().append([_('WARN'), text, acc, url])
  
  def info(self, text, acc, url=''):
    '''
    Used by validators to log informational messages.
    '''
    self.report.get_model().append([_('INFO'), text, acc, url])
    
  def debug(self, text, acc, url=''):
    '''
    Used by validators to log debug messages.
    '''
    self.report.get_model().append([_('DEBUG'), text, acc, url])
