#!/usr/bin/make

VERSION=0.47

ARCHITECTURE:=$(shell dpkg --print-architecture)

deb:
	cp -r src kathara-$(VERSION)
	rm -r kathara-$(VERSION)/debian
	tar -zcf kathara_$(VERSION).orig.tar.gz kathara-$(VERSION)
	cp -r src/debian kathara-$(VERSION)/
	cd kathara-$(VERSION); debuild -us -uc

clean:
	if [ -d kathara-$(VERSION) ]; then \
		rm -r kathara-$(VERSION); \
	fi
	if [ -e kathara_$(VERSION).orig.tar.gz ]; then \
		rm kathara_$(VERSION).orig.tar.gz; \
	fi
	if [ -e kathara_$(VERSION)-1_$(ARCHITECTURE).build ]; then \
		rm kathara_$(VERSION)-1_$(ARCHITECTURE).build; \
	fi	
	if [ -e kathara_$(VERSION)-1_$(ARCHITECTURE).buildinfo ]; then \
		rm kathara_$(VERSION)-1_$(ARCHITECTURE).buildinfo; \
	fi
	if [ -e kathara_$(VERSION)-1_$(ARCHITECTURE).changes ]; then \
		rm kathara_$(VERSION)-1_$(ARCHITECTURE).changes; \
	fi
	if [ -e kathara_$(VERSION)-1.dsc ]; then \
		rm kathara_$(VERSION)-1.dsc; \
	fi
	if [ -e kathara_$(VERSION)-1.debian.tar.xz ]; then \
		rm kathara_$(VERSION)-1.debian.tar.xz; \
	fi