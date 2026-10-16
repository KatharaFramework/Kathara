# Compiling Kathara for Linux (PKG) and Deploying on AUR

1. Check the Kathara version number in `src/Kathara/version.py`. The `Makefile` does not hold the version: pass the same one to `make` as `VERSION=x.y.z`.
2. Set your [AUR](https://aur.archlinux.org/) username and e-mail into the `Makefile`.
3. Run `make allRemote VERSION=x.y.z`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Pack the source code and all its dependencies.
    4. Push the new version on AUR. Your local SSH key (stored in `~/.ssh`) will be used to push, be sure to be authorized on AUR.
    5. Automatically remove the Docker container.

# Compiling Kathara for Linux (PKG) locally

1. Check the Kathara version number in `src/Kathara/version.py`. The `Makefile` does not hold the version: pass the same one to `make` as `VERSION=x.y.z`.
2. Run `make all VERSION=x.y.z`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Compile Kathara into a binary.
    4. Create a `.pkg` package.
    5. Automatically remove the Docker container.
3. Output file is located in the `Output` directory
