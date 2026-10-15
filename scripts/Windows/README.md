# Compiling Kathara for Windows

1. Check the Kathara version number in `src/Kathara/version.py`. The `Makefile` does not hold the version: pass the same one to `make` as `VERSION=x.y.z`.
3. Run `make all_x64 VERSION=x.y.z` (for a native arm build refer to [`windows/`](windows/README.md)). This will:
    1. Run a Docker container with pyinstaller over wine.
    2. Compile Kathara into a binary.
    3. Run a Docker container with InnoSetup over wine.
    4. Compile an installer for the binary above. 
    5. Automatically remove the containers.
4. Output file is located in the `Output` directory
