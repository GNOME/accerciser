# Accerciser 

3.46.2
Just 15 minutes a day for better accessibility!

## Description
  
  Accerciser is an interactive Python accessibility explorer for the GNOME
  desktop. It uses AT-SPI2 to inspect and control widgets, allowing you to check
  if an application is providing correct information to assistive technologies
  and automated test frameworks. Accerciser has a simple plugin framework which
  you can use to create custom views of accessibility information.

  In essence, Accerciser is a next generation at-poke tool.

# Features

- Based in at-spi2

  Accerciser uses the new dbus-based accessiblity framework.

- Plugin architecture

  Create a Python module, drop it in a folder, and have it load as a plugin pane
  with full access to AT-SPI2 and the selected element in the accessibility tree
  view.

- Interface browser and event monitor plugins

  All the features you've come to expect from a poke tool, and then some.

- IPython console plugin

  A full, interactive Python shell with access to the accessible object selected
  in the tree view; all AT-SPI2 interfaces, methods and attributes; and any other
  Python modules. Supports autocompletion and a million other niceties thanks to
  IPython.

- API browser plugin
  
  Shows the interfaces, methods, and attributes available on the selected
  accessible object.

- Global hotkeys

  Move the tree view quickly to the last focused accessible or the one under the
  mouse pointer. Insert a marker into the event monitor log for easy
  identification at a later time.

- Customizable UI layout

  Move plugin tabs to different panels or even separate windows to view them
  concurrently.

- Accessibility!

  Accerciser does not disable its own accessibility.

- Yelp documentation
  
  Included in the package.

- Python powered

  Brits, not serpents.


## Requirements

As Accerciser uses pygobject, you'll need to have the following libraries:
  ```
    gobject-introspection
    python-gobject >= 2.90.3
    gtk+3 >= 3.24.0
  ```
  On a Red Hat based distro:
  ```
    python >= 3.2
    pyatspi >= 1.9.0
    at-spi2-core >= 2.5.2
    glib2 >= 2.10
    pygobject
    python3-dbus
    python3-pyxdg
    appstream-glib-devel
    yelp-tools
  ```
  On a Debian based distro:
  ```
    meson
    pkg-config
    gettext
    yelp-tools
    appstreamcli
    libgtk-3-dev
    python3
    python3-dbus
    python-gi-dev
    python3-pyatspi >= 1.9.0
    python3-xdg
    libatspi2.0-dev >= 2.1.5
  ```
  To use the Python console plugin, you must hve IPython installed.

  Make sure accessibility is enabled for your GNOME desktop:
  ```
    gsettings get org.gnome.desktop.interface toolkit-accessibility
  ```

  
## Installing
```
  meson setup _build .
  meson compile -C _build
  sudo meson install -C _build
```
## Running

  Type `accerciser` at the prompt or choose the Accerciser item from the 
  Programming menu in GNOME.
  
## Help

  See the Help menu in the program GUI.

## Legal
  
  Copyright (c) 2006, 2007 IBM Corporation

  All rights reserved. This program and the accompanying materials are made
  available under the terms of the BSD License which accompanies this
  distribution, and is available at
  http://www.opensource.org/licenses/bsd-license.php.
  
  See COPYING and NOTICE for details.
