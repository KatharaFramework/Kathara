#!/usr/bin/make -f

VERSION=3.0.6
PACKAGE_VERSION=1
AUR_NAME=user
AUR_MAIL=my@mail.com

.PHONY: all allRemote clean docker-build-image docker-build-local docker-build-remote prepare-source prepare-man-pages prepare-bash-completion pack-source build build-aur

all: clean docker-build-image docker-build-local

allRemote: clean docker-build-image docker-build-remote

docker-build-local: docker-build-image
	docker run -ti --rm -v `pwd`/../../:/opt/kathara kathara/linux-build-pkg /usr/bin/su -c "PATH=$$PATH:/home/builduser/.gem/ruby/2.7.0/bin make build" builduser

docker-build-remote: docker-build-image
	docker run -ti --rm -v ~/.ssh:/home/builduser/.ssh -v `pwd`/../../:/opt/kathara kathara/linux-build-pkg /usr/bin/su -c "PATH=$$PATH:/home/builduser/.gem/ruby/2.7.0/bin make build-aur" builduser

docker-build-image:
	cd Docker-Linux-Build && docker build -t kathara/linux-build-pkg .

prepare-source:
	mkdir Output
	cp -r ../../src Output/kathara

prepare-man-pages:
	gem install ronn-ng
	cd ../../docs && make roff-build
	for man_file in ../../docs/Roff/*; do \
		man_file_dir="man$${man_file: -1}"; \
		[[ -d ../../docs/Roff/$$man_file_dir ]] || mkdir ../../docs/Roff/$$man_file_dir; \
		mv -f $$man_file ../../docs/Roff/$$man_file_dir; \
	done;
	mkdir -p Output/kathara/manpages
	cp -r ../../docs/Roff/* Output/kathara/manpages
	cd ../../docs && make cleanall

prepare-bash-completion:
	python3 -m pip install -r ../autocompletion/requirements.txt
	python3 ../autocompletion/generate_autocompletion.py Output/kathara/kathara.bash-completion

pack-source: prepare-source prepare-man-pages prepare-bash-completion
	cd Output/kathara && tar cfvz ../kathara.tar.gz .
	rm -Rf Output/kathara
	cp -r pacman/* Output/
	sed -i -e "s|__DATE__|$$(date -R)|g" Output/kathara.changelog
	sed -i -e 's/__VERSION__/$(VERSION)/g' Output/kathara.changelog
	sed -i -e 's/__VERSION__/$(VERSION)/g' Output/PKGBUILD
	sed -i -e 's/__PACKAGE_VERSION__/$(PACKAGE_VERSION)/g' Output/PKGBUILD

build: pack-source
	cd Output && makepkg
	rm -rf Output/kathara.changelog Output/kathara.install Output/PKGBUILD
	rm -rf Output/kathara.tar.gz
	rm -rf Output/pkg
	rm -rf Output/src

build-aur: pack-source
	cd Output && makepkg
	git clone ssh://aur@aur.archlinux.org/kathara Output/kathara-aur
	git config --global user.name "$(AUR_NAME)"
	git config --global user.email "$(AUR_MAIL)"
	cp kathara-aur/PKGBUILD Output/kathara-aur/PKGBUILD
	sed -i -e "s/__VERSION__/$(VERSION)/g" Output/kathara-aur/PKGBUILD
	sed -i -e "s/__PACKAGE_VERSION__/$(PACKAGE_VERSION)/g" Output/kathara-aur/PKGBUILD
	cd Output/kathara-aur && makepkg --printsrcinfo > .SRCINFO
	git --work-tree=Output/kathara-aur --git-dir=Output/kathara-aur/.git add .
	git --work-tree=Output/kathara-aur --git-dir=Output/kathara-aur/.git commit -m "Bump to v$(VERSION)-$(PACKAGE_VERSION)"
	git --work-tree=Output/kathara-aur --git-dir=Output/kathara-aur/.git push
	rm -rf Output/kathara.changelog Output/kathara.install Output/PKGBUILD
	rm -rf Output/kathara.tar.gz
	rm -rf Output/pkg
	rm -rf Output/src

clean:
	[ -d Output ] && rm -rf Output
