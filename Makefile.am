SUBDIRS = src icons plugins help

desktopdir = $(datadir)/applications
desktop_DATA = accerciser.desktop

schemasdir = $(GCONF_SCHEMA_FILE_DIR)
schemas_DATA = accerciser.schemas

EXTRA_DIST = $(desktop_DATA) pyreqs.py accerciser.spec gnome-doc-utils.make
DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper
DISTCLEANFILES = accerciser.desktop accerciser.spec

if GCONF_SCHEMAS_INSTALL
install-data-local:
	if test -z "$(DESTDIR)" ; then \
		for p in $(schemas_DATA) ; do \
			GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) $(GCONFTOOL) --makefile-install-rule $(srcdir)/$$p ; \
		done \
	fi
else
install-data-local:
endif
