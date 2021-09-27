#!/usr/bin/make -s

.PHONY : all
all: clean package upload


package: clean
	cd ../../ && python3 setup.py sdist --dist-dir='scripts/pip-package/dist'

upload: package
	twine upload dist/*

clean:
	rm -r dist