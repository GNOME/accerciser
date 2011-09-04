SUBDIRS = doc help icons plugindata plugins po src pixmaps

INTLTOOL = 			\
	intltool-extract.in 	\
	intltool-merge.in 	\
	intltool-update.in

desktopdir = $(datadir)/applications
desktop_in_files=accerciser.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

EXTRA_DIST =  \
	$(desktop_in_files) \
	$(desktop_DATA) \
	pyreqs.py \
	accerciser.spec \
	gnome-doc-utils.make \
	$(INTLTOOL) \
        org.a11y.Accerciser.gschema.xml

DISTCHECK_CONFIGURE_FLAGS = \
	--disable-scrollkeeper \
	--enable-pydoc
DISTCLEANFILES = \
	$(desktop_DATA) \
	accerciser.spec \
	intltool-extract \
	intltool-merge \
	intltool-update	\
	gnome-doc-utils.make

gsettings_SCHEMAS = \
        org.a11y.Accerciser.gschema.xml
 
@GSETTINGS_RULES@

