#!/usr/bin/make -f

# ?= so a local test can override it without editing this file: make docker-build_43 SET_ARCH='--platform linux/amd64' VERSION=3.8.4
# CI keeps replacing the placeholder with sed -i, which works either way.
VERSION?=__KATHARA_VERSION__
PACKAGE_VERSION=1
# Fedora release used by a plain `make all`. CI overrides it per matrix entry by calling `make docker-build_<release>` directly.
DEFAULT_RELEASE?=43
# Directory searched (recursively) for .rpm files by `make sign`.
RPM_DIR?=Output

.PHONY: all clean prepare-source prepare-man-pages prepare-bash-completion pack-source build sign cleanbinary

all: docker-build_$(DEFAULT_RELEASE)

# Pattern target: `make docker-build_43`, `make docker-build_44`, ...
# The Fedora release becomes the %{?dist} tag of the resulting package (1.fc43, 1.fc44), which is what the YUM repository uses to file the package under fedora/<releasever>/<basearch>/.
docker-build_%: clean docker-build-image_%
	docker run --rm -v `pwd`/../../:/opt/kathara -e VERSION="$(VERSION)" $(SET_ARCH) kathara/linux-build-rpm:$* /bin/bash -c \
		"make build && { chown -R $(shell id -u):$(shell id -g) Output || true; } && make cleanbinary"

# The release-specific Dockerfile is fed to docker on stdin (-f -) instead of being written next to the template.
# Nothing is created or deleted inside the working tree, so a failed build leaves no stray file behind and the target is safe to run on a dirty checkout.
docker-build-image_%:
	cd Docker-Linux-Build && sed -e "s|__RELEASE__|$*|g" Dockerfile_template \
		| docker build $(SET_ARCH) -t kathara/linux-build-rpm:$* -f - .

prepare-source:
	cp rpm/kathara.spec ~/rpmbuild/SPECS
	sed -i -e "s|__DATE__|$$(date +'%a %b %d %Y')|g" ~/rpmbuild/SPECS/kathara.spec
	sed -i -e 's/__VERSION__/$(VERSION)/g' ~/rpmbuild/SPECS/kathara.spec
	sed -i -e 's/__PACKAGE_VERSION__/$(PACKAGE_VERSION)/g' ~/rpmbuild/SPECS/kathara.spec
	mkdir -p ~/rpmbuild/SOURCES/kathara-$(VERSION)/src
	cp -r ../../src ~/rpmbuild/SOURCES/kathara-$(VERSION)
	cp kathara.pyinstaller.spec ~/rpmbuild/SOURCES/kathara-$(VERSION)/src/kathara.spec
	mkdir -p ~/rpmbuild/SOURCES/kathara-$(VERSION)/tests
	cp -r ../../tests ~/rpmbuild/SOURCES/kathara-$(VERSION)

prepare-man-pages:
	cd ../../docs && make roff-build
	for man_file in ../../docs/Roff/*; do \
		man_file_dir="man$${man_file: -1}"; \
		[[ -d ../../docs/Roff/$$man_file_dir ]] || mkdir ../../docs/Roff/$$man_file_dir; \
		mv $$man_file ../../docs/Roff/$$man_file_dir; \
	done;
	mkdir -p ~/rpmbuild/SOURCES/kathara-$(VERSION)/manpages
	cp -r ../../docs/Roff/* ~/rpmbuild/SOURCES/kathara-$(VERSION)/manpages
	cd ../../docs && make cleanall

prepare-bash-completion:
	python3.13 -m venv ~/py-build-env
	~/py-build-env/bin/pip install --upgrade "setuptools<81.0.0"
	~/py-build-env/bin/pip install -r ../autocompletion/requirements.txt
	~/py-build-env/bin/python ../autocompletion/generate_autocompletion.py ~/rpmbuild/SOURCES/kathara-$(VERSION)/kathara.bash-completion

pack-source: prepare-source prepare-man-pages prepare-bash-completion
	cd ~/rpmbuild/SOURCES/ && tar -zcf kathara-$(VERSION).tar.gz kathara-$(VERSION)
	cd ~/rpmbuild/SOURCES/ && rm -Rf kathara-$(VERSION)

build: pack-source
	rpmbuild -ba ~/rpmbuild/SPECS/kathara.spec
	mkdir -p Output
	cp -r ~/rpmbuild/RPMS/* Output


sign: SHELL=/bin/bash
sign:
	@set -euo pipefail; \
	[ -n "$${RPM_GPG_PRIVATE_KEY:-}" ] || { echo "::error::RPM_GPG_PRIVATE_KEY is not set"; exit 1; }; \
	mapfile -t pkgs < <(find "$(RPM_DIR)" -type f -name '*.rpm'); \
	[ $${#pkgs[@]} -gt 0 ] || { echo "::error::no .rpm to sign in $(RPM_DIR)"; exit 1; }; \
	export HOME="$$(mktemp -d)"; chmod 700 "$$HOME"; \
	export GNUPGHOME="$$HOME/gnupg"; mkdir -m 700 "$$GNUPGHOME"; \
	trap 'gpgconf --kill all >/dev/null 2>&1 || true; rm -rf "$$HOME"' EXIT; \
	printf '%s' "$$RPM_GPG_PRIVATE_KEY" | base64 -d | gpg --batch --quiet --import; \
	signing_key() { gpg --batch --list-secret-keys --with-colons | awk -F: -v t="$$1" '$$1==t && $$12 ~ /s/ {print $$5; exit}'; }; \
	KEYID="$$(signing_key ssb)"; \
	[ -n "$$KEYID" ] || KEYID="$$(signing_key sec)"; \
	if [ -z "$$KEYID" ]; then \
		echo "::error::the imported key has no usable signing key."; \
		echo "The secret exported into RPM_GPG_PRIVATE_KEY must contain a signing subkey (or a primary that can sign). Keys currently imported:"; \
		gpg --batch --list-secret-keys --keyid-format long || true; \
		echo "Regenerate the export with:"; \
		echo "  gpg --export-secret-subkeys --armor \"<SIGNING_SUBKEY_FPR>!\" | base64 -w0"; \
		exit 1; \
	fi; \
	echo "Signing with key $$KEYID"; \
	umask 077; \
	printf '%s' "$${RPM_GPG_PASSPHRASE:-}" > "$$HOME/passphrase"; \
	printf '%s\n' \
		'%_signature gpg' \
		"%_gpg_name $$KEYID!" \
		'%_gpg_digest_algo sha256' \
		"%_gpg_passphrase_file $$HOME/passphrase" \
		'%__gpg_sign_cmd %{__gpg} gpg --no-verbose --no-armor --no-secmem-warning --batch --pinentry-mode loopback --passphrase-file %{_gpg_passphrase_file} --digest-algo sha256 -u "%{_gpg_name}" -sbo %{__signature_filename} %{__plaintext_filename}' \
		> "$$HOME/.rpmmacros"; \
	for p in "$${pkgs[@]}"; do rpmsign --addsign "$$p"; done; \
	mkdir "$$HOME/rpmdb"; \
	rpm --dbpath "$$HOME/rpmdb" --initdb; \
	gpg --batch --armor --export "$$KEYID" > "$$HOME/pub.asc"; \
	rpmkeys --dbpath "$$HOME/rpmdb" --import "$$HOME/pub.asc"; \
	for p in "$${pkgs[@]}"; do \
		sig="$$(rpm -qpi --nosignature "$$p" 2>/dev/null | sed -n 's/^Signature *: //p')"; \
		case "$$sig" in ''|'(none)') echo "::error::$$(basename "$$p") is still unsigned"; exit 1 ;; esac; \
		rpmkeys --dbpath "$$HOME/rpmdb" --checksig "$$p" >/dev/null \
			|| { echo "::error::$$(basename "$$p") failed signature verification"; exit 1; }; \
		echo "$$(basename "$$p"): $$sig"; \
	done

clean:
	if [ -d Output ]; then \
		rm -rf Output; \
	fi

cleanbinary:
	cd /opt/kathara/src && find . | grep -E "(__pycache__|\.pyc|\.pyo)$$" | xargs rm -rf
	if [ -e /opt/kathara/src/kathara.spec ]; then \
		rm /opt/kathara/src/kathara.spec; \
	fi
	if [ -d /opt/kathara/src/kathara.build ]; then \
		rm -r /opt/kathara/src/kathara.build; \
	fi