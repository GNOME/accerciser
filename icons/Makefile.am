hicolordir = $(datadir)/icons/hicolor
app_icons =			\
	accerciser-16.png	\
	accerciser-22.png	\
	accerciser-32.png	\
	accerciser.png		\
	accerciser.svg

noinst_DATA = accerciser-small.svg

install-data-local:
	@-$(mkinstalldirs) $(DESTDIR)$(hicolordir)/scalable/apps
	$(INSTALL_DATA) $(srcdir)/accerciser.svg $(DESTDIR)$(hicolordir)/scalable/apps/accerciser.svg
	@-$(mkinstalldirs) $(DESTDIR)$(hicolordir)/16x16/apps
	$(INSTALL_DATA) $(srcdir)/accerciser-16.png $(DESTDIR)$(hicolordir)/16x16/apps/accerciser.png
	@-$(mkinstalldirs) $(DESTDIR)$(hicolordir)/22x22/apps
	$(INSTALL_DATA) $(srcdir)/accerciser-22.png $(DESTDIR)$(hicolordir)/22x22/apps/accerciser.png
	@-$(mkinstalldirs) $(DESTDIR)$(hicolordir)/32x32/apps
	$(INSTALL_DATA) $(srcdir)/accerciser-32.png $(DESTDIR)$(hicolordir)/32x32/apps/accerciser.png
	@-$(mkinstalldirs) $(DESTDIR)$(hicolordir)/48x48/apps
	$(INSTALL_DATA) $(srcdir)/accerciser.png $(DESTDIR)$(hicolordir)/48x48/apps/accerciser.png

uninstall-hook:
	rm -f $(DESTDIR)$(hicolordir)/scalable/apps/accerciser.svg
	rm -f $(DESTDIR)$(hicolordir)/16x16/apps/accerciser.png
	rm -f $(DESTDIR)$(hicolordir)/22x22/apps/accerciser.png
	rm -f $(DESTDIR)$(hicolordir)/32x32/apps/accerciser.png
	rm -f $(DESTDIR)$(hicolordir)/48x48/apps/accerciser.png
	@-if test -z "$(DESTDIR)"; then \
                echo "Updating Gtk icon cache."; \
                $(gtk_update_icon_cache); \
        else \
                echo "*** Icon cache not updated.  After uninstall, run this:"; \
                echo "***   $(gtk_update_icon_cache)"; \
        fi

gtk_update_icon_cache = gtk-update-icon-cache -f -t $(datadir)/icons/hicolor
install-data-hook:
	@-if test -z "$(DESTDIR)"; then \
		echo "Updating Gtk icon cache."; \
		$(gtk_update_icon_cache); \
	else \
		echo "*** Icon cache not updated.  After install, run this:"; \
		echo "***   $(gtk_update_icon_cache)"; \
	fi

EXTRA_DIST = $(app_icons) $(noinst_DATA)

