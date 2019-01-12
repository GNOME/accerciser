SUBDIRS = doc help icons plugindata plugins po src pixmaps

desktopdir = $(datadir)/applications
desktop_in_files=accerciser.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
$(desktop_DATA): $(desktop_in_files)
	$(AM_V_GEN)$(MSGFMT) --desktop --template $< -d $(top_srcdir)/po -o $@

gsettings_SCHEMAS = org.a11y.Accerciser.gschema.xml
@GSETTINGS_RULES@

appstream_in_files = accerciser.appdata.xml.in
appstream_XML = $(appstream_in_files:.xml.in=.xml)
$(appstream_XML): $(appstream_in_files)
	$(AM_V_GEN)$(MSGFMT) --xml --template $< -d $(top_srcdir)/po -o $@
@APPSTREAM_XML_RULES@

EXTRA_DIST =  \
	$(appstream_in_files) \
	$(desktop_in_files) \
	$(desktop_DATA) \
	pyreqs.py \
	$(gsettings_SCHEMAS)

DISTCHECK_CONFIGURE_FLAGS = \
	--disable-scrollkeeper \
	--enable-pydoc

DISTCLEANFILES = \
	$(desktop_DATA)

CLEANFILES = \
	$(appstream_XML) \
	$(desktop_DATA)
