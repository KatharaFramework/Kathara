#!/usr/bin/make -f

VERSION=3.6.3
PACKAGE_VERSION=1
AUR_NAME=user
AUR_MAIL=contact@kathara.org

.PHONY: all allRemote clean docker-build-image docker-build-local docker-build-remote build-local build-remote

all: clean docker-build-image docker-build-local

allRemote: clean docker-build-image docker-build-remote

docker-build-local: docker-build-image
	mkdir -p Output
	docker run -ti -v `pwd`:/home/builduser/kathara:ro -v `pwd`/Output:/home/builduser/output -v `pwd`/../..:/home/builduser/kathara-source/Kathara-$(VERSION):ro  kathara/linux-build-pkg /usr/bin/su -c \
		"make -f /home/builduser/kathara/Makefile build-local" builduser

docker-build-remote: docker-build-image
	docker run -ti --rm -v ~/.ssh:/home/builduser/ssh:ro -v `pwd`:/home/builduser/kathara:ro kathara/linux-build-pkg /usr/bin/su -c \
		"make -f /home/builduser/kathara/Makefile build-remote" builduser

docker-build-image:
	cd Docker-Linux-Build && docker build -t kathara/linux-build-pkg .

prepare-files:
	cp -r /home/builduser/kathara/pkginfo/* /home/builduser/build
	sed -i -e "s|__DATE__|$$(date -R)|g" /home/builduser/build/kathara.changelog
	sed -i -e 's/__VERSION__/$(VERSION)/g' /home/builduser/build/kathara.changelog
	sed -i -e 's/__VERSION__/$(VERSION)/g' /home/builduser/build/PKGBUILD
	sed -i -e 's/__PACKAGE_VERSION__/$(PACKAGE_VERSION)/g' /home/builduser/build/PKGBUILD

build-local: prepare-files
	mkdir -p /home/builduser/build/src/
	cp -r /home/builduser/kathara-source/Kathara-$(VERSION) /home/builduser/build/src
	tar -zcf /home/builduser/build/kathara-$(VERSION).tar.gz /home/builduser/build/src/Kathara-$(VERSION)
	sed -i -e 's/__PYTHON_DEP__//g' /home/builduser/build/PKGBUILD
	sed -i -e 's/__SOURCE__/"kathara-$(VERSION).tar.gz"/g' /home/builduser/build/PKGBUILD
	makepkg
	mv kathara*.pkg.tar.zst /home/builduser/output/

build-remote: prepare-files
	sed -i -e "s/__PYTHON_DEP__/'python310'/g" /home/builduser/build/PKGBUILD
	sed -i -e 's/__SOURCE__/"https:\/\/github.com\/KatharaFramework\/Kathara\/archive\/refs\/tags\/\$$\pkgver.tar.gz"/g' /home/builduser/build/PKGBUILD
	cp -r /home/builduser/ssh/ /home/builduser/.ssh/ && chmod 600 /home/builduser/.ssh/id_rsa
	ssh-keyscan aur.archlinux.org > /home/builduser/.ssh/known_hosts
	cd .. && git clone ssh://aur@aur.archlinux.org/kathara kathara-aur
	cd ../kathara-aur && git checkout master
	git config --global user.name "$(AUR_NAME)"
	git config --global user.email "$(AUR_MAIL)"
	cp -r /home/builduser/build/* ../kathara-aur/
	cd ../kathara-aur && makepkg --printsrcinfo > .SRCINFO
	cd ../kathara-aur && git add .
	cd ../kathara-aur && git commit -m "Bump to v$(VERSION)-$(PACKAGE_VERSION)"
	cd ../kathara-aur && git push

clean:
	if [ -d Output ]; then \
		rm -rf Output; \
	fi
