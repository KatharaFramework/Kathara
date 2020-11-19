# Compiling Kathara for Linux (RPM)

1. Change the Kathara version number in the following files:
    1. `src/Resources/version.py`
    2. `Makefile`
2. Write a proper `%changelog` section in `fedora/kathara.spec` file. 
3. Run `make`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Compile Kathara into a binary.
    4. Create a `.rpm` package.
    6. Automatically remove the Docker container.
4. Output file is located in the `Output` directory
