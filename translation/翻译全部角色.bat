@echo off
chcp 65001 1>nul 2>nul
pushd "%~dp0"
cd ..
python "translation\translate.py" --all
popd
pause
