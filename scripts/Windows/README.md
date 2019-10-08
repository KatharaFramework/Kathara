# Compiling Kathara for Windows

1. Download and Install Inno Setup [Quick link](http://www.jrsoftware.org/download.php/is.exe)
2. Install pyinstaller `python -m pip install pyinstaller` (from an Administrator cmd or Powershell)
3. Install Kathara python dependencies `python -m pip install -r ..\..\src\requirements.txt` (from an Administrator cmd or Powershell)
4. Create binary package running `WindowsBuild.bat`
5. Compile Inno Script Setup file
6. Share the `Kathara-setup.exe` in output folder :)