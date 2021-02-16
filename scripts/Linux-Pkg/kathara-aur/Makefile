#!/usr/bin/make -f

PKGNAME := kathara
SRCDIR := ../../../src
BUILDDIR := build
DOCSDIR := ../../../docs
AUTOCOMPDIR := ../../autocompletion

.PHONY: build

manpages:
	cd $(DOCSDIR) && make roff-build
	for man_file in $(DOCSDIR)/Roff/*; do \
		man_file_dir="man$${man_file: -1}"; \
		[[ -d $(DOCSDIR)/Roff/$$man_file_dir ]] || mkdir $(DOCSDIR)/Roff/$$man_file_dir; \
		mv -f $$man_file $(DOCSDIR)/Roff/$$man_file_dir; \
	done;

autocompletion:
	python3 -m pip install -r $(AUTOCOMPDIR)/requirements.txt
	cd $(AUTOCOMPDIR) && python3 generate_autocompletion.py ${PKGNAME}.bash-completion

build: manpages autocompletion
	python3 -m pip install -r $(SRCDIR)/requirements.txt
	[ ! -d $(BUILDDIR) ] && mkdir -p $(BUILDDIR)
	python3 -m nuitka --show-progress --plugin-enable=pylint-warnings --follow-imports --standalone --include-plugin-directory=$(SRCDIR)/Resources --output-dir=$(BUILDDIR) $(SRCDIR)/${PKGNAME}.py

install:
	install -Dm644 $(DOCSDIR)/Roff/* $(DESTDIR)$(PREFIX)/share/man/${PKGNAME}
	install -Dm644 $(AUTOCOMPDIR)/${PKGNAME}.bash-completion $(DESTDIR)$(PREFIX)/share/bash-completion/completions/${PKGNAME}
	install -Dm644 $(BUILDDIR)/*.so* $(DESTDIR)$(PREFIX)/lib/${PKGNAME}/
	install -Dm755 $(BUILDDIR)/${PKGNAME} $(DESTDIR)$(PREFIX)/lib/${PKGNAME}/
	install -Dm755 $(BUILDDIR)/certifi/* $(DESTDIR)$(PREFIX)/lib/${PKGNAME}/certifi/
	install -Dm755 $(BUILDDIR)/pyuv/* $(DESTDIR)$(PREFIX)/lib/${PKGNAME}/pyuv/
	mkdir -p $(DESTDIR)$(PREFIX)/bin
	ln -sf $(DESTDIR)$(PREFIX)/lib/${PKGNAME} $(DESTDIR)$(PREFIX)/bin/${PKGNAME}

clean:
	cd $(DOCSDIR) && make cleanall
	rm $(AUTOCOMPDIR)/${PKGNAME}.bash-completion
	rm -rf $(BUILDDIR)