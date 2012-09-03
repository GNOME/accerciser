# Calls gnome-autogen to build Makefiles and run configure

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.


GNOMEDOC=`which yelp-build`
if test -z $GNOMEDOC; then
echo "*** The tools to build the documentation are not found,"
echo " please install the yelp-tool package ***"
fi

REQUIRED_AUTOMAKE_VERSION=1.7.2
USE_GNOME2_MACROS=1 . gnome-autogen.sh
