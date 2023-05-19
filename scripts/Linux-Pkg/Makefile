#!/usr/bin/make -f

VERSION=3.6.0
PACKAGE_VERSION=1
AUR_NAME=user
AUR_MAIL=your@mail.com

.PHONY: all allRemote clean docker-build-image docker-build-local docker-build-remote prepare-source prepare-man-pages prepare-bash-completion pack-source build-local build-remote

all: clean docker-build-image docker-build-local

allRemote: clean docker-build-image docker-build-remote

docker-build-local: docker-build-image
	docker run -ti --rm -v `pwd`/../../:/opt/kathara kathara/linux-build-pkg /usr/bin/su -c "PATH=$$PATH:/home/builduser/.local/bin:/home/builduser/.gem/ruby/3.0.0/bin:/home/builduser/.local/share/gem/ruby/3.0.0/bin make build-local" builduser

docker-build-remote: docker-build-image
	docker run -ti --rm -v ~/.ssh:/opt/kathara/.ssh -v `pwd`/../../:/opt/kathara kathara/linux-build-pkg /usr/bin/su -c "PATH=$$PATH:/home/builduser/.local/bin:/home/builduser/.gem/ruby/3.0.0/bin:/home/builduser/.local/share/gem/ruby/3.0.0/bin make build-remote" builduser

docker-build-image:
	cd Docker-Linux-Build && docker build -t kathara/linux-build-pkg .

prepare-source:
	mkdir -p Output/kathara/src
	cp -r ../../src Output/kathara
	mkdir -p Output/kathara/tests
	cp -r ../../tests Output/kathara

prepare-man-pages:
	mkdir -p Output
	gem install ronn-ng
	cp -r ../../docs Output/docs
	cd Output/docs && make roff-build
	for man_file in Output/docs/Roff/*; do \
		man_file_dir="man$${man_file: -1}"; \
		[[ -d Output/docs/Roff/$$man_file_dir ]] || mkdir Output/docs/Roff/$$man_file_dir; \
		mv -f $$man_file Output/docs/Roff/$$man_file_dir; \
	done;
	mkdir -p Output/kathara/manpages
	cp -r Output/docs/Roff/* Output/kathara/manpages
	cd Output/docs && make cleanall
	rm -Rf Output/docs

prepare-bash-completion:
	mkdir -p Output
	cp -r ../autocompletion Output/autocompletion
	python3 -m pip install -r Output/autocompletion/requirements.txt
	python3 Output/autocompletion/generate_autocompletion.py Output/kathara/kathara.bash-completion
	rm -Rf Output/autocompletion

pack-source: clean prepare-source prepare-man-pages prepare-bash-completion
	cd Output/kathara && tar cfvz ../kathara.tar.gz .
	rm -Rf Output/kathara
	cp -r pkginfo/* Output/
	sed -i -e "s|__DATE__|$$(date -R)|g" Output/kathara.changelog
	sed -i -e 's/__VERSION__/$(VERSION)/g' Output/kathara.changelog
	sed -i -e 's/__VERSION__/$(VERSION)/g' Output/PKGBUILD
	sed -i -e 's/__PACKAGE_VERSION__/$(PACKAGE_VERSION)/g' Output/PKGBUILD

build-local: pack-source
	cd Output && makepkg
	rm -rf Output/kathara.changelog Output/kathara.install Output/PKGBUILD
	rm -rf Output/kathara.tar.gz
	rm -rf Output/pkg
	rm -rf Output/src

build-remote: pack-source 
	cp -r /opt/kathara/.ssh/ /home/builduser/.ssh/ && chmod 600 /home/builduser/.ssh/id_rsa
	ssh-keyscan aur.archlinux.org > /home/builduser/.ssh/known_hosts
	cd Output && git clone ssh://aur@aur.archlinux.org/kathara kathara-aur
	git config --global user.name "$(AUR_NAME)"
	git config --global user.email "$(AUR_MAIL)"
	cd Output && cp -Rf $$(ls | grep -v kathara-aur) kathara-aur/
	cd Output/kathara-aur && makepkg --printsrcinfo > .SRCINFO
	git --work-tree=Output/kathara-aur --git-dir=Output/kathara-aur/.git add .
	git --work-tree=Output/kathara-aur --git-dir=Output/kathara-aur/.git commit -m "Bump to v$(VERSION)-$(PACKAGE_VERSION)"
	git --work-tree=Output/kathara-aur --git-dir=Output/kathara-aur/.git push

clean:
	if [ -d Output ]; then \
		rm -rf Output; \
	fi
