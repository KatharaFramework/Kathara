#!/usr/bin/make -f

VERSION=3.0.3
PACKAGE_VERSION=1

.PHONY: all clean docker-build-image prepare-source prepare-man-pages prepare-bash-completion pack-source build

all: clean docker-build-image docker-build

docker-build: clean docker-build-image
	docker run -ti --rm -v `pwd`/../../:/opt/kathara kathara/linux-build-rpm /bin/bash -c "make build"

docker-build-image:
	cd Docker-Linux-Build && docker build -t kathara/linux-build-rpm .
	
prepare-source:
	cp rpm/kathara.spec ~/rpmbuild/SPECS
	sed -i -e "s|__DATE__|$$(date +'%a %b %d %Y')|g" ~/rpmbuild/SPECS/kathara.spec
	sed -i -e 's/__VERSION__/$(VERSION)/g' ~/rpmbuild/SPECS/kathara.spec
	sed -i -e 's/__PACKAGE_VERSION__/$(PACKAGE_VERSION)/g' ~/rpmbuild/SPECS/kathara.spec
	cp -r ../../src ~/rpmbuild/SOURCES/kathara-$(VERSION)

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
	python3 -m pip install -r ../autocompletion/requirements.txt
	python3 ../autocompletion/generate_autocompletion.py ~/rpmbuild/SOURCES/kathara-$(VERSION)/kathara.bash-completion

pack-source: prepare-source prepare-man-pages prepare-bash-completion
	cd ~/rpmbuild/SOURCES/ && tar -zcf kathara-$(VERSION).tar.gz kathara-$(VERSION)
	cd ~/rpmbuild/SOURCES/ && rm -Rf kathara-$(VERSION)

build: clean pack-source
	rpmbuild -ba ~/rpmbuild/SPECS/kathara.spec
	mkdir Output
	cp -r ~/rpmbuild/RPMS/* Output

clean:
	if [ -d Output ]; then \
		rm -rf Output; \
	fi
