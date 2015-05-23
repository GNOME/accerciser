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

appdatadir = $(datadir)/appdata
appdata_DATA = $(appdata_in_files:.xml.in=.xml)
appdata_in_files = org.gnome.accerciser.appdata.xml.in
@INTLTOOL_XML_RULE@

%.gschema.xml: %.gschema.xml.in
	$(AM_V_GEN) $(INTLTOOL_MERGE) -x -u --no-translations $< $@

@GSETTINGS_RULES@

EXTRA_DIST =  \
	$(appdata_in_files) \
	$(desktop_in_files) \
	$(desktop_DATA) \
	pyreqs.py \
	$(INTLTOOL) \
        $(gsettings_files)

DISTCHECK_CONFIGURE_FLAGS = \
	--disable-scrollkeeper \
	--enable-pydoc

DISTCLEANFILES = \
	$(desktop_DATA) \
	intltool-extract \
	intltool-merge \
	intltool-update	\
        $(gsettings_SCHEMAS)

CLEANFILES = \
	$(appdata_DATA)
