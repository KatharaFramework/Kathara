@ECHO OFF

python -m pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip

python -m pip install -r ..\..\src\requirements.txt
python -m pip install pytest
if %errorlevel% neq 0 exit /b %errorlevel%

copy Assets\kathara.spec ..\..\src\
copy Assets\app_icon.ico ..\..\src\

cd ..\..
python3 -m pytest
if %errorlevel% neq 0 exit /b %errorlevel%

cd src\

pyinstaller --distpath=./kathara.dist --workpath=./kathara.build kathara.spec

python -c "for p in __import__('pathlib').Path('.').rglob('*.py[co]'): p.unlink()"
python -c "for p in __import__('pathlib').Path('.').rglob('__pycache__'): p.rmdir()"
del kathara.spec
del app_icon.ico
rmdir /S /Q kathara.build

cmd.exe