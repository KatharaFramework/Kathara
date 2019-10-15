#/usr/bin/make

manual ::= "Kathara manual"

.PHONY: all

all: markdown-build roff-build html-build

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

