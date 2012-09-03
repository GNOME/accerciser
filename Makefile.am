SUBDIRS = doc help icons plugindata plugins po src pixmaps

INTLTOOL = 			\
	intltool-extract.in 	\
	intltool-merge.in 	\
	intltool-update.in

desktopdir = $(datadir)/applications
desktop_in_files=accerciser.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

gsettings_files = \
        org.a11y.Accerciser.gschema.xml.in

gsettings_SCHEMAS = $(gsettings_files:.xml.in=.xml)
@INTLTOOL_XML_NOMERGE_RULE@
@GSETTINGS_RULES@

EXTRA_DIST =  \
	$(desktop_in_files) \
	$(desktop_DATA) \
	pyreqs.py \
	accerciser.spec \
	$(INTLTOOL) \
        $(gsettings_files)

DISTCHECK_CONFIGURE_FLAGS = \
	--disable-scrollkeeper \
	--enable-pydoc

DISTCLEANFILES = \
	$(desktop_DATA) \
	accerciser.spec \
	intltool-extract \
	intltool-merge \
	intltool-update	\
        $(gsettings_SCHEMAS)

