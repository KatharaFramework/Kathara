#!/usr/bin/make -f

VERSION=3.7.9
DEBIAN_PACKAGE_VERSION=1
LAUNCHPAD_NAME=user
NO_BINARY_PACKAGES=pyroute2|pyuv|deepdiff

.PHONY: allSigned docker-build-image prepare-deb-source unpack-deb-source clean-output-folder copy-debian-folder download-pip build-man build-deb-unsigned build-deb-signed ppa clean venv autocompletion

allSigned: clean prepare-deb-source docker-signed_focal docker-signed_jammy docker-signed_noble

docker-unsigned_%: clean prepare-deb-source docker-build-image_%
	docker run -ti --rm -v `pwd`/../../:/opt/kathara kathara/linux-build-deb:$* /bin/bash -c \
	 	"make build-deb-unsigned distro=$* && chown -R $(shell id -u):$(shell id -g) Output"

docker-signed_%: docker-build-image_%
	docker run -ti --rm -v $(HOME)/.gnupg:/root/gnupg-host -v `pwd`/../../:/opt/kathara kathara/linux-build-deb:$* /bin/bash -c \
	 	"make unpack-deb-source && make build-deb-signed distro=$* && make ppa && make clean-output-folder distro=$*"

docker-build-image_%:
	cd Docker-Linux-Build && cp Dockerfile_template Dockerfile
	cd Docker-Linux-Build && sed -i -e "s|__DISTRO__|$*|g" Dockerfile
	cd Docker-Linux-Build && docker build -t kathara/linux-build-deb:$* .
	cd Docker-Linux-Build && rm Dockerfile

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
	
venv:
	python3.11 -m venv /root/py-build-env

download-pip: copy-debian-folder
	mkdir Output/kathara-$(VERSION)/debian/pythonLibs_amd64
	mkdir Output/kathara-$(VERSION)/debian/pythonLibs_arm64
	grep -Ev "$(NO_BINARY_PACKAGES)" Output/kathara-$(VERSION)/requirements.txt > Output/kathara-$(VERSION)/requirements-binary.txt
	grep -E "$(NO_BINARY_PACKAGES)" Output/kathara-$(VERSION)/requirements.txt > Output/kathara-$(VERSION)/requirements-no-binary.txt
	/root/py-build-env/bin/pip install --upgrade setuptools
	cd Output/kathara-$(VERSION)/debian/pythonLibs_amd64 && /root/py-build-env/bin/pip download --platform manylinux2014_x86_64 --only-binary=:all: flit_core
	cd Output/kathara-$(VERSION)/debian/pythonLibs_amd64 && /root/py-build-env/bin/pip download --platform manylinux2014_x86_64 --only-binary=:all: wheel
	cd Output/kathara-$(VERSION)/debian/pythonLibs_amd64 && /root/py-build-env/bin/pip download --platform manylinux2014_x86_64 --only-binary=:all: zstandard
	cd Output/kathara-$(VERSION)/debian/pythonLibs_amd64 && /root/py-build-env/bin/pip download --no-binary=:all: -r ../../requirements-no-binary.txt
	cd Output/kathara-$(VERSION)/debian/pythonLibs_amd64 && /root/py-build-env/bin/pip download --platform manylinux2014_x86_64 --platform x86_64 --only-binary=:all: -r ../../requirements-binary.txt
	cd Output/kathara-$(VERSION)/debian/pythonLibs_amd64 && /root/py-build-env/bin/pip download --no-binary=:all: nuitka==2.6.7
	cd Output/kathara-$(VERSION)/debian/pythonLibs_arm64 && /root/py-build-env/bin/pip download --platform manylinux2014_aarch64 --only-binary=:all: flit_core
	cd Output/kathara-$(VERSION)/debian/pythonLibs_arm64 && /root/py-build-env/bin/pip download --platform manylinux2014_aarch64 --only-binary=:all: wheel
	cd Output/kathara-$(VERSION)/debian/pythonLibs_arm64 && /root/py-build-env/bin/pip download --platform manylinux2014_aarch64 --only-binary=:all: zstandard
	cd Output/kathara-$(VERSION)/debian/pythonLibs_arm64 && /root/py-build-env/bin/pip download --no-binary=:all: -r ../../requirements-no-binary.txt
	cd Output/kathara-$(VERSION)/debian/pythonLibs_arm64 && /root/py-build-env/bin/pip download --platform manylinux2014_aarch64 --platform arm64 --only-binary=:all: -r ../../requirements-binary.txt
	cd Output/kathara-$(VERSION)/debian/pythonLibs_arm64 && /root/py-build-env/bin/pip download --no-binary=:all: nuitka==2.6.7
	rm Output/kathara-$(VERSION)/debian/pythonLibs_arm64/zstandard*.tar.gz
	rm Output/kathara-$(VERSION)/debian/pythonLibs_amd64/zstandard*.tar.gz
	rm -Rf Output/kathara-$(VERSION)/requirements-binary.txt Output/kathara-$(VERSION)/requirements-no-binary.txt
	ls Output/kathara-$(VERSION)/debian/pythonLibs_amd64/ | awk '{print "debian/pythonLibs_amd64/"$$0}' > Output/kathara-$(VERSION)/debian/source/include-binaries
	ls Output/kathara-$(VERSION)/debian/pythonLibs_arm64/ | awk '{print "debian/pythonLibs_arm64/"$$0}' >> Output/kathara-$(VERSION)/debian/source/include-binaries

build-man: copy-debian-folder
	cd ../../docs && make roff-build
	cp -r ../../docs/Roff Output/kathara-$(VERSION)/debian/manpages
	cd ../../docs && make cleanall
	ls Output/kathara-$(VERSION)/debian/manpages/ | awk '{print "debian/manpages/"$$0}' > Output/kathara-$(VERSION)/debian/kathara.manpages

autocompletion:
	/root/py-build-env/bin/pip install -r ../autocompletion/requirements.txt
	/root/py-build-env/bin/python3 ../autocompletion/generate_autocompletion.py Output/kathara-$(VERSION)/debian/kathara.bash-completion

build-deb-unsigned: venv build-man autocompletion download-pip
	sed -i -e 's/__UBUNTU_VERSION__/$(distro)/g' Output/kathara-$(VERSION)/debian/changelog
	cd Output/kathara-$(VERSION); debuild -us -uc

build-deb-signed: venv build-man autocompletion download-pip
	cp -r /root/gnupg-host/. /root/.gnupg
	sed -i -e 's/__UBUNTU_VERSION__/$(distro)/g' Output/kathara-$(VERSION)/debian/changelog
	cd Output/kathara-$(VERSION); debuild -S -sa

ppa:
	sed -i -e 's/__LAUNCHPAD_NAME__/$(LAUNCHPAD_NAME)/g' $(HOME)/.dput.cf
	dput -U ppa:katharaframework/kathara Output/*.changes

clean:
	if [ -d Output ]; then \
		rm -rf Output; \
	fi
