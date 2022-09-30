#!/usr/bin/make -s

PRODUCT=Kathara
VERSION=3.5.1
TARGET_DIRECTORY=Output
APPLE_DEVELOPER_CERTIFICATE_ID=FakeID
ROFF_DIR=../../docs/Roff
VENV_DIR:=${CURDIR}/venv

.PHONY: all_x86 allSigned_x86 all_arm64 allSigned_arm64 test deps manpages cleanall cleanman cleanbinary cleanenv
all: all_x86 all_arm64
allSigned: allSigned_x86 allSigned_arm64
all_x86: deps binary_x86_64 manpages createInstaller_x86_64 clean
allSigned_x86: deps binary_x86_64 manpages createInstaller_x86_64 signProduct_x86_64 clean
all_arm64: deps binary_arm64 manpages createInstaller_arm64 clean
allSigned_arm64: deps binary_arm64 manpages createInstaller_arm64 signProduct_arm64 clean

default: all

py_env:
	python3 -m venv $(VENV_DIR)

deps: py_env
	$(VENV_DIR)/bin/pip3.10 install pyinstaller
	$(VENV_DIR)/bin/pip3.10 install -r ../../src/requirements.txt
	$(VENV_DIR)/bin/pip3.10 install pytest
	gem install ronn-ng --user-install

manpages:
	cd ../../docs && make roff-build;
	
	for man_file in $(ROFF_DIR)/*; do \
		man_file_dir="man$${man_file: -1}"; \
		[[ -d $(ROFF_DIR)/$$man_file_dir ]] || mkdir $(ROFF_DIR)/$$man_file_dir; \
		mv $$man_file $(ROFF_DIR)/$$man_file_dir; \
	done;

test:
	cd ../.. && $(VENV_DIR)/bin/python3 -m pytest

binary_%: test
	cp ./kathara.spec ../../src/
	sed -i '' -e "s:__ARCH__:$*:g" ../../src/kathara.spec
	cd ../../src && $(VENV_DIR)/bin/pyinstaller --distpath=./kathara.dist --workpath=./kathara.build kathara.spec

copyBuildDirectory_%: binary_% manpages
	[ -d $(TARGET_DIRECTORY) ] || mkdir $(TARGET_DIRECTORY)
	cp -r darwin/Resources $(TARGET_DIRECTORY)/
	chmod -R 755 $(TARGET_DIRECTORY)/Resources

	sed -i '' -e 's/__VERSION__/'$(VERSION)'/g' $(TARGET_DIRECTORY)/Resources/*.html
	chmod -R 755 $(TARGET_DIRECTORY)/Resources/

	mkdir -p $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)
	mkdir -p $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/

	chmod -R 755 $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)

	cp -a ../../src/kathara.dist/. $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)
	cp -a $(ROFF_DIR)/. $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/

	chmod -R 755 $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/*
	chmod 644 $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/*/*

	mkdir -p $(TARGET_DIRECTORY)/package
	chmod -R 755 $(TARGET_DIRECTORY)/package

	cp ../../LICENSE $(TARGET_DIRECTORY)/Resources/

	cp darwin/uninstall.sh $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)

	installed_man_pages=$$(ls $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/*/* | sed -e 's:$(TARGET_DIRECTORY)/darwinpkg:rm :g' | awk '{print $$0";"}'); \
	installed_man_pages=$$(echo $$installed_man_pages | sed -e "s:\n::g"); \
	sed -i '' -e "s:__MANPAGES__:$$installed_man_pages:g" $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)/uninstall.sh


createInstaller_%: copyBuildDirectory_%
	pkgbuild --identifier org.kathara.kathara --version $(VERSION) --scripts darwin/scripts \
	--root $(TARGET_DIRECTORY)/darwinpkg $(TARGET_DIRECTORY)/package/$(PRODUCT).pkg > /dev/null 2>&1
	
	productbuild --distribution darwin/Distribution --resources $(TARGET_DIRECTORY)/Kathara \
	--package-path $(TARGET_DIRECTORY)/package $(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-$*-$(VERSION).pkg > /dev/null 2>&1


signProduct_%:
	productsign --sign "Developer ID Installer: $(APPLE_DEVELOPER_CERTIFICATE_ID)" $(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-$*-$(VERSION).pkg \
	$(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-$*-$(VERSION)-signed.pkg

	pkgutil --check-signature $(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-$*-$(VERSION)-signed.pkg

clean: cleanbinary cleanman cleanenv
	if [ -d $(TARGET_DIRECTORY)/Resources ]; then \
		rm -Rf $(TARGET_DIRECTORY)/Resources; \
	fi
	if [ -d $(TARGET_DIRECTORY)/darwinpkg ]; then \
		rm -Rf $(TARGET_DIRECTORY)/darwinpkg; \
	fi
	if [ -d $(TARGET_DIRECTORY)/package ]; then \
		rm -Rf $(TARGET_DIRECTORY)/package; \
	fi

cleanall: cleanbinary cleanman cleanenv
	if [ -d ../../src/kathara.dist ]; then \
		rm -r ../../src/kathara.dist; \
	fi
	if [ -d $(TARGET_DIRECTORY) ]; then \
		rm -Rf $(TARGET_DIRECTORY); \
	fi

cleanbinary:
	cd ../../src && find . | grep -E "(__pycache__|\.pyc|\.pyo)$$" | xargs rm -rf
	if [ -e ../../src/kathara.spec ]; then \
		rm ../../src/kathara.spec; \
	fi
	if [ -d ../../src/kathara.build ]; then \
		rm -r ../../src/kathara.build; \
	fi

cleanman:
	if [ -d $(ROFF_DIR) ]; then \
		rm -Rf $(ROFF_DIR); \
	fi

cleanenv:
	if [ -d $(VENV_DIR) ]; then \
		rm -Rf $(VENV_DIR); \
	fi