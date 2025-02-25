# Compiling Kathara for Windows

1. Download and Install Inno Setup ([Quick link](http://www.jrsoftware.org/download.php/is.exe))
2. Download and Install Python 3.11 ([Quick link](https://www.python.org/downloads/release/python-3117/))
3. Add Inno Setup and Python 3.11 to the PATH environment variable
4. Change the Kathara version number in both `src/Kathara/version.py` and `installer.iss` files.
5. Create binary package running `WindowsBuild.bat`
6. Share the `Kathara-setup.exe` in output folder :)