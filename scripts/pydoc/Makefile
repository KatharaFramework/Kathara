#!/usr/bin/make -s

.PHONY: all doc verify-doc clean

all: clean doc verify-doc

doc: clean verify-doc
	python3 generate_doc.py
	cd docs && rm Kathara.model.md Kathara.setting.md Kathara.manager.md
	sed -i "" '/manager.md/d' ./docs/Kathara-API-Docs.md
	sed -i "" '/setting.md/d' ./docs/Kathara-API-Docs.md
	sed -i "" '/docker.md/d' ./docs/Kathara-API-Docs.md
	sed -i "" '/kubernetes.md/d' ./docs/Kathara-API-Docs.md
	sed -i "" '/KubernetesSettingsAddon.md/d' ./docs/Kathara-API-Docs.md
	sed -i "" '/DockerSettingsAddon.md/d' ./docs/Kathara-API-Docs.md
	sed -i "" '/model.md/d' ./docs/Kathara-API-Docs.md
	sed -i "" 's/\.\///g' ./docs/Kathara-API-Docs.md
	sed -i "" 's/\.md//g' ./docs/Kathara-API-Docs.md
	sed -i "" '/Modules/,/Classes/d' ./docs/Kathara-API-Docs.md
	sed -i "" '/Functions/q' ./docs/Kathara-API-Docs.md
	sed -i "" '/Functions/d' ./docs/Kathara-API-Docs.md

verify-doc:
	python3 -m pip install lazydocs
	lazydocs --validate ../../src/Kathara/manager --no-remove-package-prefix
	lazydocs --validate ../../src/Kathara/model --no-remove-package-prefix
	lazydocs --validate ../../src/Kathara/setting --no-remove-package-prefix
	rm -rf docs

clean:
	if [ -d docs ]; then \
		rm -rf docs; \
	fi
