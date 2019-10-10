#!/usr/bin/make -s

PRODUCT=Kathara
VERSION=0.47
TARGET_DIRECTORY=Output
APPLE_DEVELOPER_CERTIFICATE_ID=FakeID

.PHONY : all allSigned
all: deps binary createInstaller clean
allSigned: deps binary createInstaller signProduct clean

default: all

deps:
	python3 -m pip install pyinstaller
	python3 -m pip install -r ../../src/requirements.txt

binary:
	cp ./kathara.spec ../../src/
	cd ../../src && pyinstaller --distpath=./kathara.dist --workpath=./kathara.build kathara.spec

clean: cleanbinary
	if [ -d $(TARGET_DIRECTORY)/Resources ]; then \
		rm -r $(TARGET_DIRECTORY)/Resources; \
	fi
	if [ -d $(TARGET_DIRECTORY)/darwinpkg ]; then \
		rm -r $(TARGET_DIRECTORY)/darwinpkg; \
	fi
	if [ -d $(TARGET_DIRECTORY)/package ]; then \
		rm -r $(TARGET_DIRECTORY)/package; \
	fi

cleanbinary:
	cd ../../src && find . | grep -E "(__pycache__|\.pyc|\.pyo)$$" | xargs rm -rf
	if [ -e ../../src/kathara.spec ]; then \
		rm ../../src/kathara.spec; \
	fi
	if [ -d ../../src/kathara.build ]; then \
		rm -r ../../src/kathara.build; \
	fi

copyDarwinDirectory:
	mkdir $(TARGET_DIRECTORY)
	cp -r darwin/Resources $(TARGET_DIRECTORY)/
	chmod -R 755 $(TARGET_DIRECTORY)/Resources

copyBuildDirectory: copyDarwinDirectory binary
	sed -i '' -e 's/__VERSION__/'$(VERSION)'/g' $(TARGET_DIRECTORY)/Resources/*.html
	sed -i '' -e 's/__PRODUCT__/'$(PRODUCT)'/g' $(TARGET_DIRECTORY)/Resources/*.html
	chmod -R 755 $(TARGET_DIRECTORY)/Resources/

	mkdir -p $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)
	cp -a ../../src/kathara.dist/. $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)
	chmod -R 755 $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)

	mkdir -p $(TARGET_DIRECTORY)/package
	chmod -R 755 $(TARGET_DIRECTORY)/package

	cp ../../LICENSE $(TARGET_DIRECTORY)/Resources/

	cp darwin/uninstall.sh $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)

createInstaller: copyBuildDirectory
	pkgbuild --identifier org.kathara.kathara --version $(VERSION) --scripts darwin/scripts \
	--root $(TARGET_DIRECTORY)/darwinpkg $(TARGET_DIRECTORY)/package/$(PRODUCT).pkg > /dev/null 2>&1
	
	productbuild --distribution darwin/Distribution --resources $(TARGET_DIRECTORY)/Resources \
	--package-path $(TARGET_DIRECTORY)/package $(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-x64-$(VERSION).pkg > /dev/null 2>&1


signProduct:
	productsign --sign "Developer ID Installer: $(APPLE_DEVELOPER_CERTIFICATE_ID)" $(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-x64-$(VERSION).pkg \
	$(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-x64-$(VERSION)-signed.pkg

	pkgutil --check-signature $(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-x64-$(VERSION)-signed.pkg

cleanall: cleanbinary
	if [ -d ../../src/kathara.dist ]; then \
		rm -r ../../src/kathara.dist; \
	fi
	if [ -d $(TARGET_DIRECTORY) ]; then \
		rm -r $(TARGET_DIRECTORY); \
	fi

