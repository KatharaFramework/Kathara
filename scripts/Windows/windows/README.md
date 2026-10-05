# Compiling Kathara for Windows

1. Download and Install Inno Setup ([Quick link](http://www.jrsoftware.org/download.php/is.exe))
```
winget install -e --id JRSoftware.InnoSetup --accept-source-agreements --accept-package-agreements --scope machine
```
2. Download and Install Python 3.13 ([Quick link](https://www.python.org/downloads/release/python-31311/)) 
```
winget install -e --id Python.Python.3.13 --accept-source-agreements --accept-package-agreements
```
3. Add Inno Setup and Python 3.13 to the PATH environment variable
```
SET PATH=%PATH%;%programfiles(x86)%\Inno Setup 6\
```
4. Change the Kathara version number in both `src\Kathara\version.py` and `installer.iss` files.
5. Create binary package running `WindowsBuild.bat`
6. Share the `Kathara-windows-installer.exe` in output folder :)
