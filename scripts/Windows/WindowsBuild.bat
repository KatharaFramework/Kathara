set VENV_DIR=%cd%\venv

rmdir /S /Q %VENV_DIR%

python -m venv %VENV_DIR%
if %errorlevel% neq 0 exit /b %errorlevel%
CALL %VENV_DIR%\Scripts\activate
if %errorlevel% neq 0 exit /b %errorlevel%

pip install win_inet_pton
pip install pyinstaller==6.9.0
pip install -r ..\..\src\requirements.txt
pip install pytest
if %errorlevel% neq 0 exit /b %errorlevel%

copy Assets\kathara.spec ..\..\src\
copy Assets\app_icon.ico ..\..\src\

cd ..\..
pytest
if %errorlevel% neq 0 exit /b %errorlevel%

cd src\

pyinstaller --distpath=./kathara.dist --workpath=./kathara.build kathara.spec

python -c "for p in __import__('pathlib').Path('.').rglob('*.py[co]'): p.unlink()"
python -c "for p in __import__('pathlib').Path('.').rglob('__pycache__'): p.rmdir()"

del kathara.spec
del app_icon.ico

rmdir /S /Q kathara.build

CALL %VENV_DIR%\Scripts\deactivate
rmdir /S /Q %VENV_DIR%

cmd.exe