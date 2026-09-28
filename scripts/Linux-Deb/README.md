# Compiling Kathara Unsigned for Linux (DEB)

1. Change the Kathara version number in the following files:
    1. `src/Kathara/version.py`
    2. `Makefile`
2. Write a proper `debian/changelog` file. 
3. Run `make docker-unsigned`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Compile Kathara into a binary.
    4. Create a unsigned `.deb` package.
    6. Automatically remove the Docker container.
4. Output file is located in the `Output` directory
