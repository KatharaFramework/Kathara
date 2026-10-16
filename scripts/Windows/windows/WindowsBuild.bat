set VENV_DIR=%cd%\venv

rmdir /S /Q %VENV_DIR%

python -m venv %VENV_DIR%
if %errorlevel% neq 0 exit /b %errorlevel%
CALL %VENV_DIR%\Scripts\activate
if %errorlevel% neq 0 exit /b %errorlevel%

pip install --upgrade "setuptools<81"
pip install win_inet_pton
pip install "pyinstaller==6.18.0"
pip install -r ..\..\..\src\requirements.txt
pip install pytest
if %errorlevel% neq 0 exit /b %errorlevel%

copy ..\..\common\kathara.spec ..\..\..\src\
copy ..\..\common\app_icon.ico ..\..\..\src\

cd ..\..\..
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

copy ..\LICENSE ..\scripts\Windows\windows

cd ..\scripts\Windows\windows
set "arch=%PROCESSOR_ARCHITECTURE%"
if /I "%arch%"=="AMD64" (
    set "arch_suffix=x64"
) else if /I "%arch%"=="ARM64" (
    set "arch_suffix=arm64"
) else (
    set "arch_suffix=x86"
)

copy ..\..\common\kathara.spec Assets\
copy ..\..\common\app_icon.ico Assets\

iscc /DMyArchitecture=%arch_suffix% .\installer.iss
cmd.exe