dnl a macro to run a Python script with a return value
dnl AM_CHECK_PYSCRIPT(SCRIPTNAME [, PASS [, FAIL]])
AC_DEFUN([AM_CHECK_PYSCRIPT],
[AC_REQUIRE([AM_PATH_PYTHON])
AC_MSG_CHECKING($1)
if $PYTHON $1
  then
    AC_MSG_RESULT(yes)
    ifelse([$2], [], , [$2])
  else
    AC_MSG_RESULT(no)
    ifelse([$3], [], , [$3])
fi
])


dnl AM_CHECK_PYMOD(MODNAME [,SYMBOL [,ACTION-IF-FOUND [,ACTION-IF-NOT-FOUND]]])
dnl Check if a module containing a given symbol is visible to python.
AC_DEFUN([AM_CHECK_PYMOD],
[AC_REQUIRE([AM_PATH_PYTHON])
py_mod_var=`echo $1['_']$2 | sed 'y%./+-%__p_%'`
AC_MSG_CHECKING(for ifelse([$2],[],,[$2 in ])python module $1)
AC_CACHE_VAL(py_cv_mod_$py_mod_var, [
ifelse([$2],[], [prog="
import sys
try:
	import $1
except ImportError:
	sys.exit(1)
except:
	sys.exit(0)
sys.exit(0)"], [prog="
import $1
import $1.$2"])
if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC
  then
    eval "py_cv_mod_$py_mod_var=yes"
  else
    eval "py_cv_mod_$py_mod_var=no"
  fi
])
py_val=`eval "echo \`echo '$py_cv_mod_'$py_mod_var\`"`
if test "x$py_val" != xno; then
  AC_MSG_RESULT(yes)
  ifelse([$3], [],, [$3
])dnl
else
  AC_MSG_RESULT(no)
  ifelse([$4], [],, [$4
])dnl
fi
])
