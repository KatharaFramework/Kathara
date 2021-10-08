#!/usr/bin/make -s

.PHONY : all
all: clean package upload

package: clean
	cd ../../ && python3 setup.py sdist --dist-dir='scripts/pip-package/dist'

upload: package
	python3 -m pip install twine
	twine upload dist/*

clean:
	if [ -d dist ]; then \
		rm -rf dist; \
	fi
