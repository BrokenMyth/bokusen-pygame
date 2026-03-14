@echo off
chcp 65001 1>nul 2>nul
pushd "%~dp0"
cd ..
echo 1 = favorites only
echo 2 = all
set /p choice=Enter 1 or 2: 
if "%choice%"=="1" python "translation\translate.py" --favorites
if "%choice%"=="2" python "translation\translate.py" --all
if not "%choice%"=="1" if not "%choice%"=="2" python "translation\translate.py" --all
popd
pause
