#!/usr/bin/make

VERSION=0.47

ARCHITECTURE:=$(shell dpkg --print-architecture)

deb:
	mkdir Output
	cp -r ../../src Output/kathara-$(VERSION)
	cd Output && tar -zcf kathara_$(VERSION).orig.tar.gz kathara-$(VERSION)
	cp -r debian Output/kathara-$(VERSION)/
	# cd Output/kathara-$(VERSION); debuild -us -uc

clean:
	if [ -d Output ]; then \
		rm -r Output; \
	fi