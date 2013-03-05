highcontrast_dir = $(datadir)/icons/HighContrast
app_icons = accerciser.svg

install-data-local:
	@-$(mkinstalldirs) $(DESTDIR)$(highcontrast_dir)/scalable/apps
	$(INSTALL_DATA) $(srcdir)/accerciser.svg $(DESTDIR)$(highcontrast_dir)/scalable/apps/accerciser.svg

uninstall-hook:
	rm -f $(DESTDIR)$(highcontrast_dir)/scalable/apps/accerciser.svg
	@-if test -z "$(DESTDIR)"; then \
                echo "Updating Gtk icon cache."; \
                $(gtk_update_icon_cache); \
        else \
                echo "*** Icon cache not updated.  After uninstall, run this:"; \
                echo "***   $(gtk_update_icon_cache)"; \
        fi

gtk_update_icon_cache = gtk-update-icon-cache -f -t $(datadir)/icons/HighContrast
install-data-hook:
	@-if test -z "$(DESTDIR)"; then \
		echo "Updating Gtk icon cache."; \
		$(gtk_update_icon_cache); \
	else \
		echo "*** Icon cache not updated.  After install, run this:"; \
		echo "***   $(gtk_update_icon_cache)"; \
	fi

EXTRA_DIST = $(app_icons)

