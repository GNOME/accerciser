SUBDIRS = src icons plugins help

desktopdir = $(datadir)/applications
desktop_DATA = accerciser.desktop

EXTRA_DIST = $(desktop_DATA) pyreqs.py accerciser.spec gnome-doc-utils.make
DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper
DISTCLEANFILES = accerciser.desktop accerciser.spec
