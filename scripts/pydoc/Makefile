#!/usr/bin/make -s

.PHONY: all doc verify-doc clean

all: doc

doc: clean verify-doc
	python3 generate_doc.py
	cd docs && rm Kathara.model.md Kathara.setting.md Kathara.manager.md Kathara.decorators.md Kathara.event.* \
 		Kathara.foundation.md Kathara.foundation.manager.md Kathara.foundation.model.md \
 		Kathara.manager.docker.terminal.md Kathara.manager.docker.exec_stream.md Kathara.manager.docker.md \
 		Kathara.foundation.manager.stats.md Kathara.foundation.manager.terminal.md Kathara.setting.addon.md \
 		Kathara.foundation.manager.exec_stream.md Kathara.manager.docker.stats.md Kathara.manager.kubernetes.stats.md \
 		Kathara.manager.kubernetes.md Kathara.manager.kubernetes.terminal.md Kathara.os.* Kathara.parser.netkit.md \
 		Kathara.manager.kubernetes.exec_stream.md Kathara.strings.md Kathara.utils.md Kathara.parser.md Kathara.md

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
