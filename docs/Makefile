#/usr/bin/make

manual ::= "Kathara manual"

.PHONY: all

all: $(foreach name,$(shell basename -as .ronn *.ronn),MD/$(name).markdown) $(foreach name,$(shell basename -as .ronn *.ronn),Roff/$(name)) $(foreach name,$(shell basename -as .ronn *.ronn),Html/$(name).html)

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
	rm -r Html
	rm -r Roff
	rm -r MD
