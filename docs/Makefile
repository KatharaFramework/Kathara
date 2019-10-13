#/usr/bin/make

manual ::= "Kathara manual"

all: $(foreach name,$(shell basename -as .ronn *.ronn),MD/$(name).markdown)	$(foreach name,$(shell basename -as .ronn *.ronn),Roff/$(name)) $(foreach name,$(shell basename -as .ronn *.ronn),Html/$(name).html)

MD/%.markdown: %.ronn footer.md | MD/
	cat $^ | ronn --manual=$(manual) -o $(dir $@) --markdown > $@

Roff/%: %.ronn footer.md | Roff/
	cat $^ | ronn --manual=$(manual) -o $(dir $@) --roff > $@

Html/%.html: %.ronn footer.md | Html/
	cat $^ | ronn --manual=$(manual) -o $(dir $@) --html > $@

MD/:
	mkdir $@

Roff/:
	mkdir $@

Html/:
	mkdir $@
