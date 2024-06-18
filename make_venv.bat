@echo off
set PYDIR=ProjectBoardUtils\venv
rmdir /S /Q %PYDIR%
python -m venv %PYDIR%
call %PYDIR%\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt