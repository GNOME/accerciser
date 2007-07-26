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
