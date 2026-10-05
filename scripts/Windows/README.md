# Compiling Kathara for Windows

1. Change the Kathara version number in the following files:
    1. `src/Kathara/version.py`
    2. `Makefile`
3. Run `make all_x64` (for a native arm build refer to [`windows/`](windows/README.md)). This will:
    1. Run a Docker container with pyinstaller over wine.
    2. Compile Kathara into a binary.
    3. Run a Docker container with InnoSetup over wine.
    4. Compile an installer for the binary above. 
    5. Automatically remove the containers.
4. Output file is located in the `Output` directory
