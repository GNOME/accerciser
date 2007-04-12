SUBDIRS = help icons plugins po src pixmaps

INTLTOOL = 			\
	intltool-extract.in 	\
	intltool-merge.in 	\
	intltool-update.in

desktopdir = $(datadir)/applications
desktop_DATA = accerciser.desktop

schemasdir = $(GCONF_SCHEMA_FILE_DIR)
schemas_in_files = accerciser.schemas.in
schemas_DATA = $(schemas_in_files:.schemas.in=.schemas)
@INTLTOOL_SCHEMAS_RULE@

EXTRA_DIST =  \
	$(desktop_DATA) \
	pyreqs.py \
	accerciser.spec \
	gnome-doc-utils.make \
	$(INTLTOOL) \
	$(schemas_in_files) \
	$(schemas_DATA)

DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper
DISTCLEANFILES = \
	accerciser.desktop \
	accerciser.spec \
	intltool-extract \
	intltool-merge \
	intltool-update	\
	gnome-doc-utils.make \
	$(schemas_DATA)

if GCONF_SCHEMAS_INSTALL
install-data-local:
	if test -z "$(DESTDIR)" ; then \
		for p in $(schemas_DATA) ; do \
			GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) $(GCONFTOOL) --makefile-install-rule $(srcdir)/$$p ; \
		done \
	fi
uninstall-local:
	for p in $(schemas_DATA) ; do \
		GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) $(GCONFTOOL) --makefile-uninstall-rule $(srcdir)/$$p ; \
	done
else
install-data-local:
uninstall-local:
endif

