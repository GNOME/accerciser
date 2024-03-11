subdir('plugin')

lib_i18n_py = configure_file(
  input: 'i18n.py.in',
  output: '@BASENAME@',
  configuration: {
    'GETTEXT_PACKAGE': meson.project_name(),
    'localedir': get_option('localedir'),
    'prefix': get_option('prefix'),
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
