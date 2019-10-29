# Compiling Kathara for Linux

1. Change the Kathara version number in the following files:
    1. `src/Resources/version.py`
    2. `Makefile`
    3. `debian/changelog`
2. Set your [LaunchPad](https://launchpad.net/) name into the `Makefile`.
3. Set the right `Uploaders` in `debian/control` and write a proper `debian/changelog` file.
4. Ensure you have a PGP key registered on your host and on the [Ubuntu Keyserver](http://keyserver.ubuntu.com/).
5. Run `make docker`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Create a signed `.deb` package. Your PGP key will be used, so passphrase will be asked.
    4. Push the new version on LaunchPad. The LaunchPad password associated to the name set in the `Makefile` will be asked.
    5. Automatically remove the Docker container.