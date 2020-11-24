#!/usr/bin/make -f

VERSION=3.0.3
PACKAGE_VERSION=1

.PHONY: all clean docker-build-image prepare-source prepare-man-pages prepare-bash-completion pack-source build

all: clean docker-build-image docker-build

docker-build: clean docker-build-image
	docker run -ti --rm -v `pwd`/../../:/opt/kathara kathara/linux-build-arch /usr/bin/su -c "PATH=$$PATH:/home/builduser/.gem/ruby/2.7.0/bin make build" builduser

docker-build-image:
	cd Docker-Linux-Build && docker build -t kathara/linux-build-arch .
	
prepare-source:
	cp -r ../../src ~/kathara	

prepare-man-pages:
	gem install ronn-ng 
	cd ../../docs && make roff-build
	for man_file in ../../docs/Roff/*; do \
		man_file_dir="man$${man_file: -1}"; \
		[[ -d ../../docs/Roff/$$man_file_dir ]] || mkdir ../../docs/Roff/$$man_file_dir; \
		mv -f $$man_file ../../docs/Roff/$$man_file_dir; \
	done;
	mkdir -p ~/kathara/manpages
	cp -r ../../docs/Roff/* ~/kathara/manpages
	cd ../../docs && make cleanall

prepare-bash-completion:
	python3 -m pip install -r ../autocompletion/requirements.txt
	python3 ../autocompletion/generate_autocompletion.py ~/kathara/kathara.bash-completion

pack-source: prepare-source prepare-man-pages prepare-bash-completion
	cd ~/kathara && tar cfvz ~/kathara.tar.gz .
	mv ~/kathara.tar.gz .
	rm -Rf ~/kathara

build: clean pack-source
	cd pacman && makepkg -f

clean:
	if [ -d Output ]; then \
		rm -rf Output; \
	fi
