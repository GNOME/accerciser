fs = import('fs')

subdir('plugin')

localedir = get_option('localedir')
if not fs.is_absolute(localedir)
    localedir = join_paths(get_option('prefix'), localedir)
endif

lib_i18n_py = configure_file(
  input: 'i18n.py.in',
  output: '@BASENAME@',
  configuration: {
    'GETTEXT_PACKAGE': meson.project_name(),
    'localedir': localedir,
  }
)

lib_sources = [
  '__init__.py',
  'about_dialog.py',
  'accerciser.py',
  'accessible_treeview.py',
  'bookmarks.py',
  'hotkey_manager.py',
  'icons.py',
  'main_window.py',
  'menus.py',
  'node.py',
  'prefs_dialog.py',
  'tools.py',
  'window_manager.py',
]

python3.install_sources(
  [ lib_sources, lib_i18n_py ],
  subdir: meson.project_name(),
)
