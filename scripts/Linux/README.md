# Compiling Kathara Signed for Linux

1. Change the Kathara version number in the following files:
    1. `src/Resources/version.py`
    2. `Makefile`
    3. `debian/changelog`
2. Set your [LaunchPad](https://launchpad.net/) name into the `Makefile`.
3. Write a proper `debian/changelog` file.
4. Ensure you have a PGP key registered on your host and on [LaunchPad](https://launchpad.net/).
5. Run `make dockerSigned`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Compile Kathara into a binary.
    4. Create a signed source package. Your PGP key will be used, so passphrase will be asked.
    5. Push the new version on LaunchPad. The LaunchPad password associated to the name set in the `Makefile` will be asked.
    6. Automatically remove the Docker container.
4. Output files are located in the `Output` directory

# Compiling Kathara Unsigned for Linux

1. Change the Kathara version number in the following files:
    1. `src/Resources/version.py`
    2. `Makefile`
    3. `debian/changelog`
2. Write a proper `debian/changelog` file.
3. Run `make dockerUnsigned`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Compile Kathara into a binary.
    4. Create a unsigned `.deb` package.
    6. Automatically remove the Docker container.
4. Output files are located in the `Output` directory