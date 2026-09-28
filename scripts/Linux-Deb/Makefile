#!/usr/bin/make -f

VERSION?=__KATHARA_VERSION__
DEBIAN_PACKAGE_VERSION=1
OS=ubuntu

.PHONY: docker-build-image prepare-deb-source unpack-deb-source clean-output-folder copy-debian-folder build-man build-deb-unsigned clean venv autocompletion


docker-unsigned_%: clean docker-build-image_%
	docker run --rm -v `pwd`/../../:/opt/kathara -e VERSION="$(VERSION)" $(SET_ARCH) kathara/linux-build-deb:$* /bin/bash -c \
		"cp -a /opt/kathara /tmp/kathara && \
		 cd /tmp/kathara/scripts/Linux-Deb && \
		 make prepare-deb-source build-deb-unsigned distro=$* && \
		 mkdir -p /opt/kathara/scripts/Linux-Deb/Output && \
		 cp Output/*.deb /opt/kathara/scripts/Linux-Deb/Output/ && \
		 { chown -R $(shell id -u):$(shell id -g) /opt/kathara/scripts/Linux-Deb/Output || true; }"

docker-build-image_%:
	cd Docker-Linux-Build && cp Dockerfile_template Dockerfile
	cd Docker-Linux-Build && sed -i -e "1s|__DISTRO__|$*|g" Dockerfile
	if [ $* = "bookworm" ] ; then \
		cd Docker-Linux-Build && sed -i -e "s|__DISTRO__|jammy|g" Dockerfile; \
	elif [ $* = "trixie" ] ; then \
		cd Docker-Linux-Build && sed -i -e "s|__DISTRO__|noble|g" Dockerfile; \
	elif [ $* = "forky" ] ; then \
		cd Docker-Linux-Build && sed -i -e "s|__DISTRO__|resolute|g" Dockerfile; \
	else \
		cd Docker-Linux-Build && sed -i -e "s|__DISTRO__|$*|g" Dockerfile; \
	fi
	cd Docker-Linux-Build && sed -i -e "s|__OS__|$(OS)|g" Dockerfile
	cd Docker-Linux-Build && docker build $(SET_ARCH) -t kathara/linux-build-deb:$* .
	cd Docker-Linux-Build && rm Dockerfile

prepare-deb-source:
	mkdir Output
	cp -r ../../src Output/kathara-$(VERSION)
	cp ./kathara.spec Output/kathara-$(VERSION)/
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
	if [ -z "$$(which python3.14)" ] ; then \
		sed -i 's|python3.14|python3.13|g' Output/kathara-$(VERSION)/debian/control ; \
		sed -i 's|python3.14|python3.13|g' Output/kathara-$(VERSION)/debian/rules   ; \
	fi
	sed -i -e "s|__DATE__|$$(date -R)|g" Output/kathara-$(VERSION)/debian/changelog
	sed -i -e 's/__DEBIAN_PACKAGE_VERSION__/$(DEBIAN_PACKAGE_VERSION)/g' Output/kathara-$(VERSION)/debian/changelog
	sed -i -e 's/__VERSION__/$(VERSION)/g' Output/kathara-$(VERSION)/debian/changelog
	
venv:
	if [ -z "$$(which python3.14)" ] ; then \
		python3.13 -m venv /root/py-build-env ; \
	else \
		python3.14 -m venv /root/py-build-env ; \
	fi

build-man: copy-debian-folder
	cd ../../docs && make roff-build
	cp -r ../../docs/Roff Output/kathara-$(VERSION)/debian/manpages
	cd ../../docs && make cleanall
	ls Output/kathara-$(VERSION)/debian/manpages/ | awk '{print "debian/manpages/"$$0}' > Output/kathara-$(VERSION)/debian/kathara.manpages

autocompletion:
	/root/py-build-env/bin/pip install --upgrade "setuptools<81.0.0"
	/root/py-build-env/bin/pip install -r ../autocompletion/requirements.txt
	/root/py-build-env/bin/python3 ../autocompletion/generate_autocompletion.py Output/kathara-$(VERSION)/debian/kathara.bash-completion

build-deb-unsigned: venv build-man autocompletion
	sed -i -e 's/__UBUNTU_VERSION__/$(distro)/g' Output/kathara-$(VERSION)/debian/changelog
	cd Output/kathara-$(VERSION); debuild -us -uc

clean:
	if [ -d Output ]; then \
		rm -rf Output; \
	fi
