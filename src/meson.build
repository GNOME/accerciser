subdir('lib')

configure_file(
  input: 'accerciser.in',
  output: '@BASENAME@',
  configuration: {
    'PYTHON': python3.full_path(),
    'PYTHON_VERSION': python3.language_version(),
    'prefix': get_option('prefix'),
    'VERSION': meson.project_version(),
    'PACKAGE': meson.project_name(),
  },
  install: true,
  install_dir: get_option('bindir'),
)

configure_file(
  input: 'wnck-window-infos.py',
  output: 'wnck-window-infos.py',
  configuration: {
    'PYTHON': python3.full_path(),
  },
  install: true,
  install_dir: get_option('datadir') / meson.project_name(),
)
