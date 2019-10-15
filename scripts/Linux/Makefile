#!/usr/bin/make

VERSION=0.47

ARCHITECTURE:=$(shell dpkg --print-architecture)

deb:
	mkdir Output
	cp -r ../../src Output/kathara-$(VERSION)
	cd Output && tar -zcf kathara_$(VERSION).orig.tar.gz kathara-$(VERSION)
	cp -r debian Output/kathara-$(VERSION)/
	cd ../../docs && make roff-build
	cp -r ../../docs/Roff Output/kathara-$(VERSION)/debian/manpages
	cd ../../docs && make cleanall
	ls Output/kathara-$(VERSION)/debian/manpages/ | awk '{print "debian/manpages/"$$0}' > Output/kathara-$(VERSION)/debian/kathara.manpages
	cd Output/kathara-$(VERSION); debuild -us -uc

deps:
	gem install ronn-ng

clean:
	if [ -d Output ]; then \
		rm -r Output; \
	fi