#!/usr/bin/make -s

PRODUCT=Kathara
VERSION=3.8.3
TARGET_DIRECTORY=Output
APPLE_DEVELOPER_CERTIFICATE_ID=FakeID
APPLE_CERTIFICATE_PATH=
APPLE_CERTIFICATE_PASSWORD=
comma:=,
ROFF_DIR="../../docs/Roff"
VENV_DIR:="${CURDIR}/venv"

.PHONY: all allSigned manpages clean cleanall cleanman cleanbinary cleanenv tart-build-image tart-clean-image

all: cleanall
	$(MAKE) package_x86_64
	$(MAKE) package_arm64

allSigned: cleanall
	$(MAKE) packageSigned_x86_64
	$(MAKE) packageSigned_arm64

package_%: deps_% createInstaller_%
	$(MAKE) clean

packageSigned_%: deps_% createInstaller_% signProduct_%
	$(MAKE) clean

# $(1): extra `tart run` flags, $(2): commands to run in the VM before make, $(3): make targets
define tart_build
	tart list --source local --quiet | grep -qx kathara-osx-build || $(MAKE) tart-build-image
	tart delete kathara-build > /dev/null 2>&1 || true
	tart clone kathara-osx-build kathara-build
	nohup tart run --no-graphics --dir=kathara:$(CURDIR)/../.. $(1) kathara-build > /dev/null 2>&1 &
	until tart exec kathara-build true > /dev/null 2>&1; do sleep 2; done
	tart exec kathara-build zsh -lc "$(2) cd '/Volumes/My Shared Files/kathara/scripts/OSX' && make APPLE_DEVELOPER_CERTIFICATE_ID='$(APPLE_DEVELOPER_CERTIFICATE_ID)' $(3)"; status=$$?; tart stop kathara-build; tart delete kathara-build; exit $$status
endef

tart-build_%:
	$(call tart_build,,,$(if $(filter all,$*),all,cleanall package_$*))

tart-buildSigned_%:
	[ -f "$(APPLE_CERTIFICATE_PATH)" ] || { echo "Set APPLE_CERTIFICATE_PATH to the Developer ID Installer .p12 file"; exit 1; }
	$(call tart_build,--dir=certs:$(dir $(abspath $(APPLE_CERTIFICATE_PATH))):ro,\
		security unlock-keychain -p admin login.keychain && \
		security import '/Volumes/My Shared Files/certs/$(notdir $(APPLE_CERTIFICATE_PATH))' -k login.keychain -P '$(APPLE_CERTIFICATE_PASSWORD)' -T /usr/bin/productsign && \
		security set-key-partition-list -S apple-tool:$(comma)apple: -s -k admin login.keychain > /dev/null &&,\
		$(if $(filter all,$*),allSigned,cleanall packageSigned_$*))

tart-build-image: tart-clean-image
	tart clone ghcr.io/cirruslabs/macos-tahoe-base:latest kathara-img
	nohup tart run --no-graphics kathara-img > /dev/null 2>&1 &
	until tart exec kathara-img true > /dev/null 2>&1; do sleep 2; done
	tart exec -i kathara-img /bin/bash -s < Tart-OSX-Build/provision.sh
	tart stop kathara-img
	tart rename kathara-img kathara-osx-build

tart-clean-image:
	tart delete kathara-osx-build > /dev/null 2>&1 || true
	tart delete kathara-img > /dev/null 2>&1 || true

py_env_%:
	arch -$* python3.13 -m venv $(VENV_DIR)

deps_%: py_env_%
	arch -$* $(VENV_DIR)/bin/python3 -m pip install -U "setuptools<81"
	arch -$* $(VENV_DIR)/bin/python3 -m pip install "pyinstaller==6.18.0"
	arch -$* $(VENV_DIR)/bin/python3 -m pip install -r ../../src/requirements.txt
	arch -$* $(VENV_DIR)/bin/python3 -m pip install pytest

manpages:
	cd ../../docs && make roff-build;
	
	for man_file in $(ROFF_DIR)/*; do \
		man_file_dir="man$${man_file: -1}"; \
		[[ -d $(ROFF_DIR)/$$man_file_dir ]] || mkdir $(ROFF_DIR)/$$man_file_dir; \
		mv $$man_file $(ROFF_DIR)/$$man_file_dir; \
	done;

test_%:
	cd ../.. && arch -$* $(VENV_DIR)/bin/python3 -m pytest

binary_%: test_%
	cp ./kathara.spec ../../src/
	sed -i '' -e "s:__ARCH__:$*:g" ../../src/kathara.spec
	cd ../../src && arch -$* $(VENV_DIR)/bin/python3 -m PyInstaller --distpath=./kathara.dist --workpath=./kathara.build kathara.spec

copyBuildDirectory_%: binary_% manpages
	[ -d $(TARGET_DIRECTORY) ] || mkdir $(TARGET_DIRECTORY)
	cp -r darwin/Resources $(TARGET_DIRECTORY)/
	chmod -R 755 $(TARGET_DIRECTORY)/Resources

	sed -i '' -e 's/__VERSION__/'$(VERSION)'/g' $(TARGET_DIRECTORY)/Resources/*.html
	chmod -R 755 $(TARGET_DIRECTORY)/Resources/

	mkdir -p $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)
	mkdir -p $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/

	chmod -R 755 $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)

	cp -r ../../src/kathara.dist/kathara/_internal $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)/_internal
	find $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)/_internal -type f -exec chmod 644 {} \;
	cp -a ../../src/kathara.dist/kathara/kathara $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)/
	cp -a $(ROFF_DIR)/. $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/

	chmod -R 755 $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/*
	chmod 644 $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/*/*

	cp ../../LICENSE $(TARGET_DIRECTORY)/Resources/

	cp darwin/uninstall.sh $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)

	installed_man_pages=$$(ls $(TARGET_DIRECTORY)/darwinpkg/usr/local/share/man/*/* | sed -e 's:$(TARGET_DIRECTORY)/darwinpkg:rm :g' | awk '{print $$0";"}'); \
	installed_man_pages=$$(echo $$installed_man_pages | sed -e "s:\n::g"); \
	sed -i '' -e "s:__MANPAGES__:$$installed_man_pages:g" $(TARGET_DIRECTORY)/darwinpkg/Library/$(PRODUCT)/uninstall.sh

createInstaller_%: copyBuildDirectory_%
	chmod +x darwin/scripts/*
	rm -rf /tmp/kathara && mkdir -p /tmp/kathara
	pkgbuild --identifier org.kathara.kathara --version $(VERSION) --scripts darwin/scripts \
		--root $(TARGET_DIRECTORY)/darwinpkg /tmp/kathara/$(PRODUCT).pkg > /dev/null 2>&1

	productbuild --distribution darwin/Distribution --resources $(TARGET_DIRECTORY)/Resources \
		--package-path /tmp/kathara /tmp/kathara/$(PRODUCT)-macos-installer-$*-$(VERSION).pkg > /dev/null 2>&1
	cp /tmp/kathara/$(PRODUCT)-macos-installer-$*-$(VERSION).pkg $(TARGET_DIRECTORY)/
	rm -rf /tmp/kathara

signProduct_%:
	rm -rf /tmp/kathara && mkdir -p /tmp/kathara
	productsign --sign "Developer ID Installer: $(APPLE_DEVELOPER_CERTIFICATE_ID)" $(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-$*-$(VERSION).pkg \
		/tmp/kathara/$(PRODUCT)-macos-installer-$*-$(VERSION)-signed.pkg
	cp /tmp/kathara/$(PRODUCT)-macos-installer-$*-$(VERSION)-signed.pkg $(TARGET_DIRECTORY)/
	rm -rf /tmp/kathara

	pkgutil --check-signature $(TARGET_DIRECTORY)/$(PRODUCT)-macos-installer-$*-$(VERSION)-signed.pkg

clean: cleanbinary cleanman cleanenv
	if [ -d $(TARGET_DIRECTORY)/Resources ]; then \
		rm -Rf $(TARGET_DIRECTORY)/Resources; \
	fi
	if [ -d $(TARGET_DIRECTORY)/darwinpkg ]; then \
		rm -Rf $(TARGET_DIRECTORY)/darwinpkg; \
	fi

cleanall: cleanbinary cleanman cleanenv
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
	if [ -d ../../src/kathara.dist ]; then \
		rm -r ../../src/kathara.dist; \
	fi
	if [ -d ../../src/kathara.spec ]; then \
		rm -r ../../src/kathara.spec; \
	fi