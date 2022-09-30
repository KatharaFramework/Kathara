# Compiling Kathara for Windows

1. Download and Install Inno Setup ([Quick link](http://www.jrsoftware.org/download.php/is.exe))
2. Download and Install Python 3.10 ([Quick link](https://www.python.org/downloads/release/python-3107/))
3. Install pyinstaller `python -m pip install pyinstaller` (from an Administrator cmd or Powershell)
3. Install Kathara python dependencies `python -m pip install -r ..\..\src\requirements.txt` (from an Administrator cmd or Powershell)
4. Change the Kathara version number in both `src/Kathara/version.py` and `installer.iss` files.
5. Create binary package running `WindowsBuild.bat`
6. Compile Inno Script Setup file
7. Share the `Kathara-setup.exe` in output folder :)