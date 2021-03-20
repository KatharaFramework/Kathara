# Compiling Kathara for Linux (PKG) and Deploying on AUR

1. Change the Kathara version number in the following files:
    1. `src/Resources/version.py`
    2. `Makefile`
2. Set your [AUR](https://aur.archlinux.org/) username and e-mail into the `Makefile`.
3. Write a proper `changelog` section in `pkginfo/kathara.changelog` file. 
4. Run `make allRemote`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Pack the source code and all its dependencies.
    4. Push the new version on AUR. Your local SSH key (stored in `~/.ssh`) will be used to push, be sure to be authorized on AUR.
    5. Automatically remove the Docker container.

# Compiling Kathara for Linux (PKG) locally

1. Change the Kathara version number in the following files:
    1. `src/Resources/version.py`
    2. `Makefile`
2. Write a proper `changelog` section in `pkginfo/kathara.changelog` file. 
3. Run `make`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Compile Kathara into a binary.
    4. Create a `.pkg` package.
    5. Automatically remove the Docker container.
4. Output file is located in the `Output` directory
