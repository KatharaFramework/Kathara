# Compiling Kathara Unsigned for Linux (DEB)

1. Check the Kathara version number in `src/Kathara/version.py`. The `Makefile` does not hold the version: pass the same one to `make` as `VERSION=x.y.z`.
2. Run `make docker-unsigned_<distro> OS=<os> VERSION=x.y.z`. This will:
    1. Create a proper Docker image for the build environment
    2. Run a Docker container with the image built above.
    3. Compile Kathara into a binary.
    4. Create a unsigned `.deb` package.
    5. Automatically remove the Docker container.
3. Output file is located in the `Output` directory

# Changelog

To see the package changelog before building, run `make changelog VERSION=x.y.z distro=<distro>`.
If `CHANGELOG.md` has no section for `x.y.z` yet, a "Development build" entry is added on top.
