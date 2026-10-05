#!/usr/bin/make -f

# ?= so a local test can override it without editing this file: make docker-build_43 SET_ARCH='--platform linux/amd64' VERSION=3.8.4
# CI keeps replacing the placeholder with sed -i, which works either way.
VERSION?=__KATHARA_VERSION__
PACKAGE_VERSION=1
# Fedora release used by a plain `make all`. CI overrides it per matrix entry by calling `make docker-build_<release>` directly.
DEFAULT_RELEASE=43

.PHONY: all clean prepare-source prepare-man-pages prepare-bash-completion pack-source build cleanbinary

all: docker-build_$(DEFAULT_RELEASE)

# Pattern target: `make docker-build_43`, `make docker-build_44`, ...
# The Fedora release becomes the %{?dist} tag of the resulting package (1.fc43, 1.fc44), which is what the YUM repository uses to file the package under fedora/<releasever>/<basearch>/.
docker-build_%: clean docker-build-image_%
	docker run --rm -v `pwd`/../../:/opt/kathara -e VERSION="$(VERSION)" $(SET_ARCH) kathara/linux-build-rpm:$* /bin/bash -c \
		"make build && { chown -R $(shell id -u):$(shell id -g) Output || true; } && make cleanbinary"

# The release-specific Dockerfile is fed to docker on stdin (-f -) instead of being written next to the template.
# Nothing is created or deleted inside the working tree, so a failed build leaves no stray file behind and the target is safe to run on a dirty checkout.
docker-build-image_%:
	cd Docker-Linux-Build && sed -e "s|__RELEASE__|$*|g" Dockerfile_template \
		| docker build $(SET_ARCH) -t kathara/linux-build-rpm:$* -f - .

prepare-source:
	cp rpm/kathara.spec ~/rpmbuild/SPECS
	sed -i -e "s|__DATE__|$$(date +'%a %b %d %Y')|g" ~/rpmbuild/SPECS/kathara.spec
	sed -i -e 's/__VERSION__/$(VERSION)/g' ~/rpmbuild/SPECS/kathara.spec
	sed -i -e 's/__PACKAGE_VERSION__/$(PACKAGE_VERSION)/g' ~/rpmbuild/SPECS/kathara.spec
	mkdir -p ~/rpmbuild/SOURCES/kathara-$(VERSION)/src
	cp -r ../../src ~/rpmbuild/SOURCES/kathara-$(VERSION)
	cp kathara.pyinstaller.spec ~/rpmbuild/SOURCES/kathara-$(VERSION)/src/kathara.spec
	mkdir -p ~/rpmbuild/SOURCES/kathara-$(VERSION)/tests
	cp -r ../../tests ~/rpmbuild/SOURCES/kathara-$(VERSION)

prepare-man-pages:
	cd ../../docs && make roff-build
	for man_file in ../../docs/Roff/*; do \
		man_file_dir="man$${man_file: -1}"; \
		[[ -d ../../docs/Roff/$$man_file_dir ]] || mkdir ../../docs/Roff/$$man_file_dir; \
		mv $$man_file ../../docs/Roff/$$man_file_dir; \
	done;
	mkdir -p ~/rpmbuild/SOURCES/kathara-$(VERSION)/manpages
	cp -r ../../docs/Roff/* ~/rpmbuild/SOURCES/kathara-$(VERSION)/manpages
	cd ../../docs && make cleanall

prepare-bash-completion:
	python3.13 -m venv ~/py-build-env
	~/py-build-env/bin/pip install --upgrade "setuptools<81.0.0"
	~/py-build-env/bin/pip install -r ../autocompletion/requirements.txt
	~/py-build-env/bin/python ../autocompletion/generate_autocompletion.py ~/rpmbuild/SOURCES/kathara-$(VERSION)/kathara.bash-completion

pack-source: prepare-source prepare-man-pages prepare-bash-completion
	cd ~/rpmbuild/SOURCES/ && tar -zcf kathara-$(VERSION).tar.gz kathara-$(VERSION)
	cd ~/rpmbuild/SOURCES/ && rm -Rf kathara-$(VERSION)

build: pack-source
	rpmbuild -ba ~/rpmbuild/SPECS/kathara.spec
	mkdir -p Output
	cp -r ~/rpmbuild/RPMS/* Output

clean:
	if [ -d Output ]; then \
		rm -rf Output; \
	fi

cleanbinary:
	cd /opt/kathara/src && find . | grep -E "(__pycache__|\.pyc|\.pyo)$$" | xargs rm -rf
	if [ -e /opt/kathara/src/kathara.spec ]; then \
		rm /opt/kathara/src/kathara.spec; \
	fi
	if [ -d /opt/kathara/src/kathara.build ]; then \
		rm -r /opt/kathara/src/kathara.build; \
	fi