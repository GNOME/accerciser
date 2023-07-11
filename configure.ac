AC_INIT([Accerciser],
        [3.40.0],
        [https://gitlab.gnome.org/GNOME/accerciser/issues],
        [accerciser])

AC_CONFIG_SRCDIR(src/accerciser.in)
AM_INIT_AUTOMAKE([1.11 check-news])
AM_MAINTAINER_MODE([enable])

YELP_HELP_INIT

dnl == check for python ==
AM_PATH_PYTHON(3.2)

dnl == requeriments ==
GTK_REQUIRED=3.24.0
PYGOBJECT_REQUIRED=2.90.3
ATSPI_REQUIRED=2.5.2
GLIB_GSETTINGS

dnl == check for requeriments ==
PKG_CHECK_MODULES([GTK], [gtk+-3.0 >= $GTK_REQUIRED])
PKG_CHECK_MODULES([PYGOBJECT], [pygobject-3.0 >= $PYGOBJECT_REQUIRED])
PKG_CHECK_MODULES([ATSPI2], [atspi-2 >= $ATSPI_REQUIRED])

dnl == check for python modules
AM_CHECK_PYMOD(IPython,,[ipython_support="yes"],[AC_MSG_WARN(Could not find python module: IPython);ipython_support="no"])

dnl == i18n ==
# FIXME: Remove AM_GNU_GETTEXT_VERSION once autoreconf supports REQUIRE_VERSION
AM_GNU_GETTEXT_VERSION([0.19.8])
AM_GNU_GETTEXT_REQUIRE_VERSION([0.19.8])
AM_GNU_GETTEXT([external])
GETTEXT_PACKAGE=accerciser
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [The gettext package])

APPSTREAM_XML

dnl == generate makefiles ==
AC_OUTPUT([
Makefile
doc/Makefile
help/Makefile
icons/Makefile
icons/hicolor/Makefile
pixmaps/Makefile
plugins/Makefile
plugindata/Makefile
plugindata/validate/Makefile
po/Makefile.in
src/accerciser
src/Makefile
src/lib/Makefile
src/lib/accerciser/i18n.py
src/lib/accerciser/Makefile
src/lib/accerciser/plugin/Makefile
])

dnl =============================================================================================
echo "
Accerciser $VERSION

        Installation prefix:     ${prefix}
        IPython support:         ${ipython_support}

"
