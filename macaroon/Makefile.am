SUBDIRS = bin macaroon po

desktopdir = $(datadir)/applications
desktop_in_files=macaroon.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
$(desktop_DATA): $(desktop_in_files)
	$(AM_V_GEN)$(MSGFMT) --desktop --template $< -d $(top_srcdir)/po -o $@

EXTRA_DIST =  \
	$(desktop_in_files) \
	$(desktop_DATA) \
	pyreqs.py \
	TODO

DISTCLEANFILES = \
	$(desktop_DATA)


