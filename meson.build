project('accerciser',
  version: '3.46.2',
  meson_version: '>= 1.0.0',
)

# Importing modules
python = import('python')
gnome = import('gnome')
i18n = import('i18n')

# Python
python3 = python.find_installation('python3', required: true)
min_py3_version = '3.2'
if not python3.language_version().version_compare(f'>= @min_py3_version@')
  error(f'Python @min_py3_version@ or newer is required.')
endif

# (slightly awkward) check if some Python modules are available.
# See https://github.com/mesonbuild/meson/issues/3551
python_modules = {}

foreach _module : [ 'IPython' ]
  # Source: https://docs.python.org/3/library/importlib.html#checking-if-a-module-can-be-imported
  script = f'import importlib.util; import sys; exit(1) if importlib.util.find_spec(\'@_module@\') is None else exit(0)'
  mod_available = (run_command(python3, '-c', script, check: false).returncode() == 0)
  python_modules += { _module: mod_available }
endforeach

# Useful variables
po_dir = meson.project_source_root() / 'po'

# Dependencies
gtk_dep = dependency('gtk+-3.0', version: '>= 3.24.0')
pyobject_dep = dependency('pygobject-3.0', version: '>= 2.90.3')
atspi_dep = dependency('atspi-2', version: '>= 2.5.2')

# Desktop file
desktop_file = i18n.merge_file(
  input: 'accerciser.desktop.in',
  output: '@BASENAME@',
  type: 'desktop',
  po_dir: po_dir,
  install: true,
  install_dir: get_option('datadir') / 'applications',
)
# Validating the desktop file
desktop_file_validate = find_program('desktop-file-validate', required:false)
if desktop_file_validate.found()
  test (
    'validate-desktop',
    desktop_file_validate,
    args: [ desktop_file.full_path() ],
    depends: [ desktop_file ],
  )
endif

# Appdata file
appdata_file = i18n.merge_file(
  input: 'org.gtk.accerciser.metainfo.xml.in',
  output: '@BASENAME@',
  type: 'xml',
  po_dir: po_dir,
  install: true,
  install_dir: get_option('datadir') / 'metainfo',
)
# Validate the appdata file
appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('validate-appdata', appstreamcli,
    args: [
      'validate', '--no-net', '--explain', appdata_file.full_path()
    ],
    depends: [ appdata_file, ],
  )
endif

# GSettings
compiled = gnome.compile_schemas()
install_data('org.a11y.Accerciser.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)

# Post-install
gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)

# Subdirectories
subdir('doc')
subdir('gnome-shell-extension')
subdir('help')
subdir('icons')
subdir('kwin-scripts')
subdir('plugindata')
subdir('plugins')
subdir('po')
subdir('src')
subdir('pixmaps')

# Summary
summary({
  'prefix': get_option('prefix'),
  'IPython Support': python_modules['IPython'],
})
