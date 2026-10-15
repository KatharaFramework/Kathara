# Compiling Kathara for Linux (RPM)

1. Check the Kathara version number in `src/Kathara/version.py`. The `Makefile` does not hold the version: pass the same one to `make` as `VERSION=x.y.z`.
2. Write a proper `%changelog` section in `rpm/kathara.spec` file. 
3. Run `make all VERSION=x.y.z`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Compile Kathara into a binary.
    4. Create a `.rpm` package.
    5. Automatically remove the Docker container.
4. Output file is located in the `Output` directory
