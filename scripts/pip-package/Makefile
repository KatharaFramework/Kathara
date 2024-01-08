#!/usr/bin/make -s

.PHONY: all package upload clean
all: clean package upload

package: clean
	cd ../../ && python3 -m build --outdir='scripts/pip-package/dist'

upload: package
	python3 -m pip install twine
	twine upload dist/*

clean:
	if [ -d dist ]; then \
		rm -rf dist; \
	fi
