#!/usr/bin/make -f

VERSION=3.0.5
DEBIAN_PACKAGE_VERSION=1
LAUNCHPAD_NAME=user

.PHONY: allSigned docker-unsigned docker-signed_% docker-build-image prepare-deb-source unpack-deb-source clean-output-folder copy-debian-folder download-pip build-man build-deb-unsigned build-deb-signed ppa deps clean

allSigned: clean docker-build-image prepare-deb-source docker-signed_bionic docker-signed_focal docker-signed_groovy

docker-unsigned: clean prepare-deb-source docker-build-image
	docker run -ti --rm -v `pwd`/../../:/opt/kathara kathara/linux-build /bin/bash -c "make build-deb-unsigned"

docker-signed_%:
	docker run -ti --rm -v $(HOME)/.gnupg:/root/.gnupg -v `pwd`/../../:/opt/kathara kathara/linux-build /bin/bash -c "make unpack-deb-source && make build-deb-signed distro=$* && make ppa && make clean-output-folder distro=$*"

docker-build-image:
	cd Docker-Linux-Build && docker build -t kathara/linux-build .

prepare-deb-source:
	mkdir Output
	cp -r ../../src Output/kathara-$(VERSION)
	cd Output; tar -zcf kathara_$(VERSION).orig.tar.gz kathara-$(VERSION)

unpack-deb-source:
	cd Output; tar -xvf kathara_$(VERSION).orig.tar.gz

clean-output-folder:
	rm -rf Output/kathara-$(VERSION)
	rm -rf Output/kathara_$(VERSION)-$(DEBIAN_PACKAGE_VERSION)$(distro).debian.tar.xz
	rm -rf Output/kathara_$(VERSION)-$(DEBIAN_PACKAGE_VERSION)$(distro).dsc
	rm -rf Output/kathara_$(VERSION)-$(DEBIAN_PACKAGE_VERSION)$(distro)_source.build
	rm -rf Output/kathara_$(VERSION)-$(DEBIAN_PACKAGE_VERSION)$(distro)_source.buildinfo
	rm -rf Output/kathara_$(VERSION)-$(DEBIAN_PACKAGE_VERSION)$(distro)_source.changes

copy-debian-folder:
	cp -r debian Output/kathara-$(VERSION)/
	sed -i -e "s|__DATE__|$$(date -R)|g" Output/kathara-$(VERSION)/debian/changelog
	sed -i -e 's/__DEBIAN_PACKAGE_VERSION__/$(DEBIAN_PACKAGE_VERSION)/g' Output/kathara-$(VERSION)/debian/changelog
	sed -i -e 's/__VERSION__/$(VERSION)/g' Output/kathara-$(VERSION)/debian/changelog

download-pip: copy-debian-folder
	mkdir Output/kathara-$(VERSION)/debian/pythonLibs
	cd Output/kathara-$(VERSION)/debian/pythonLibs; python3 -m pip download -r ../../requirements.txt
	cd Output/kathara-$(VERSION)/debian/pythonLibs; python3 -m pip download nuitka
	ls Output/kathara-$(VERSION)/debian/pythonLibs/ | awk '{print "debian/pythonLibs/"$$0}' > Output/kathara-$(VERSION)/debian/source/include-binaries

build-man: copy-debian-folder
	cd ../../docs && make roff-build
	cp -r ../../docs/Roff Output/kathara-$(VERSION)/debian/manpages
	cd ../../docs && make cleanall
	ls Output/kathara-$(VERSION)/debian/manpages/ | awk '{print "debian/manpages/"$$0}' > Output/kathara-$(VERSION)/debian/kathara.manpages

	/usr/bin/python3 -m pip install -r autocompletion/requirements.txt
	/usr/bin/python3 autocompletion/generate_autocompletion.py "Output/kathara-$(VERSION)/debian/kathara.bash-completion"

build-deb-unsigned: build-man download-pip
	sed -i -e 's/__UBUNTU_VERSION__/focal/g' Output/kathara-$(VERSION)/debian/changelog
	cd Output/kathara-$(VERSION); debuild -us -uc

build-deb-signed: build-man download-pip
	sed -i -e 's/__UBUNTU_VERSION__/$(distro)/g' Output/kathara-$(VERSION)/debian/changelog
	cd Output/kathara-$(VERSION); debuild -S -sa

ppa:
	sed -i -e 's/__LAUNCHPAD_NAME__/$(LAUNCHPAD_NAME)/g' $(HOME)/.dput.cf
	dput -U ppa:katharaframework/kathara Output/*.changes

deps:
	gem install ronn-ng

clean:
	if [ -d Output ]; then \
		rm -rf Output; \
	fi
