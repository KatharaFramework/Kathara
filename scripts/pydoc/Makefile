#!/usr/bin/make -s

.PHONY: all doc verify-doc clean

all: clean doc verify-doc

doc: clean verify-doc
	python3 generate_doc.py
	cd docs && rm Kathara.model.md Kathara.setting.md Kathara.manager.md
	sed '/manager.md/d' ./docs/Kathara-API-Docs.md
	sed '/setting.md/d' ./docs/Kathara-API-Docs.md
	sed '/docker.md/d' ./docs/Kathara-API-Docs.md
	sed '/kubernetes.md/d' ./docs/Kathara-API-Docs.md
	sed '/KubernetesSettingsAddon.md/d' ./docs/Kathara-API-Docs.md
	sed '/DockerSettingsAddon.md/d' ./docs/Kathara-API-Docs.md
	sed '/model.md/d' ./docs/Kathara-API-Docs.md
	sed 's/\.\///g' ./docs/Kathara-API-Docs.md
	sed 's/\.md//g' ./docs/Kathara-API-Docs.md
	sed '/Modules/,/Classes/d' ./docs/Kathara-API-Docs.md
	sed '/Functions/q' ./docs/Kathara-API-Docs.md
	sed '/Functions/d' ./docs/Kathara-API-Docs.md

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
