#!/usr/bin/make -f

manual ::= "Kathara manual"

.PHONY: all

all: markdown-build roff-build html-build docker-build-image build-%

build-%: docker-build-image
	docker run -ti --rm -v `pwd`:/root/docs kathara/linux-build-deb /bin/bash -c "cd /root/docs && make $*-build"

docker-build-image:
	cp ../scripts/Linux-Deb/Docker-Linux-Build/Dockerfile_template ../scripts/Linux-Deb/Docker-Linux-Build/Dockerfile
	sed -i -e "s|__DISTRO__|focal|g" ../scripts/Linux-Deb/Docker-Linux-Build/Dockerfile
	cd ../scripts/Linux-Deb/Docker-Linux-Build/ && docker build -t kathara/linux-build-deb .
	rm -f ../scripts/Linux-Deb/Docker-Linux-Build/Dockerfile

markdown-build: $(foreach name,$(shell basename -as .ronn *.ronn),MD/$(name).markdown)
roff-build: $(foreach name,$(shell basename -as .ronn *.ronn),Roff/$(name))
html-build: $(foreach name,$(shell basename -as .ronn *.ronn),Html/$(name).html)

MD/%.markdown: %.ronn | MD/
	cat $^ | m4 -P | ronn --manual=$(manual) -o $(dir $@) --markdown > $@

Roff/%: %.ronn | Roff/
	cat $^ | m4 -P | ronn --manual=$(manual) -o $(dir $@) --roff > $@

Html/%.html: %.ronn | Html/
	cat $^ | m4 -P | ronn --manual=$(manual) -o $(dir $@) --html > $@

MD/:
	mkdir $@

Roff/:
	mkdir $@

Html/:
	mkdir $@

cleanall:
	if [ -d Html ]; then \
		rm -r Html; \
	fi
	if [ -d Roff ]; then \
		rm -r Roff; \
	fi
	if [ -d MD ]; then \
		rm -r MD; \
	fi
	if [ -d scripts ]; then \
		rm -r scripts; \
	fi
