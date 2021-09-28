# Create a Kathara package for PyPI (pip)

1. Install `twine`. On Debian based:
```
sudo apt install twine
```
2. Change the Kathara version number in the following files:
    1. `src/Kathara/version.py`.
    2. `setup.py` (change `version` and `download_url`).
3. Run `make all`. This will:
   1. Create a Kathara Python package.
   2. Upload the packet on PyPI.
4. Output files are located in the `dist` directory.