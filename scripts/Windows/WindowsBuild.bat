@ECHO OFF

python -m pip install -r ..\..\src\requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%

copy kathara.spec ..\..\src\

cd ..\..\src

pyinstaller --distpath=./kathara.dist --workpath=./kathara.build kathara.spec

python -c "for p in __import__('pathlib').Path('.').rglob('*.py[co]'): p.unlink()"
python -c "for p in __import__('pathlib').Path('.').rglob('__pycache__'): p.rmdir()"
del kathara.spec
rmdir /S /Q kathara.build