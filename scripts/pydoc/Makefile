#!/usr/bin/make -s

.PHONY: all doc verify-doc clean

all: doc

doc: clean verify-doc
	python3 generate_doc.py
	cd docs && rm Kathara.model.md Kathara.setting.md Kathara.manager.md Kathara.decorators.md Kathara.event.* \
 		Kathara.foundation.*  Kathara.manager.docker.terminal.md Kathara.manager.kubernetes.terminal.md Kathara.os.* \
 		Kathara.parser.netkit.md Kathara.strings.md Kathara.utils.md

	sed -i 's/\.\///' docs/Kathara-API-Docs.md
	sed -i 's/\.md//' docs/Kathara-API-Docs.md
	sed -i '/Modules/,/Classes/{/Classes/!d;}' docs/Kathara-API-Docs.md
	rm docs/.pages

verify-doc:
	python3 -m pip install lazydocs pydocstyle
	lazydocs --validate ../../src/Kathara/manager --no-remove-package-prefix
	lazydocs --validate ../../src/Kathara/model --no-remove-package-prefix
	lazydocs --validate ../../src/Kathara/setting --no-remove-package-prefix
	rm -rf docs

clean:
	if [ -d docs ]; then \
		rm -rf docs; \
	fi
