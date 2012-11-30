AC_INIT([Accerciser],[3.7.1pre],[eitan@ascender.com],[accerciser])
AC_CONFIG_SRCDIR(src/accerciser.in)
AM_INIT_AUTOMAKE
AM_MAINTAINER_MODE([enable])

YELP_HELP_INIT

dnl == check for python ==
AM_PATH_PYTHON(2.7)

dnl == requeriments ==
GTK_REQUIRED=3.1.13
PYGOBJECT_REQUIRED=2.90.3
ATSPI_REQUIRED=2.1.5
GLIB_GSETTINGS

dnl == check for requeriments ==
PKG_CHECK_MODULES([GTK], [gtk+-3.0 >= GTK_REQUIRED])
PKG_CHECK_MODULES([PYGOBJECT], [pygobject-3.0 >= PYGOBJECT_REQUIRED])
PKG_CHECK_MODULES([ATSPI2], [atspi-2 >= ATSPI_REQUIRED])

dnl == i18n ==
GETTEXT_PACKAGE=accerciser
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [The gettext package])
AM_GLIB_GNU_GETTEXT

dnl == intltool check ==
IT_PROG_INTLTOOL([0.35.0])

dnl == generate makefiles ==
AC_OUTPUT([
Makefile
accerciser.spec
accerciser.desktop.in
doc/Makefile
help/Makefile
icons/Makefile
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

