# Create a Kathara package for PyPI (pip)

1. Change the Kathara version number in the following files:
    1. `src/Kathara/version.py`.
    2. `setup.py` (change `version` and `download_url`).
2.Run `make all`. This will:
    3. Create a proper python package.
    4. Upload the packet on PyPI.
4. Output file is located in the `dist` directory
