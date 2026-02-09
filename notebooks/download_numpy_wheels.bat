@echo off
REM Download numpy wheels for multiple Python versions and platforms
REM Run this on machine with internet, then copy numpy_wheels folder to offline machine

echo === Download NumPy Wheels for Offline ===
echo.

if not exist "numpy_wheels" mkdir numpy_wheels
cd numpy_wheels

echo Downloading NumPy 1.26.4 for Python 3.10, 3.11, 3.12...

REM Python 3.10
pip download numpy==1.26.4 --python-version 3.10 --platform manylinux2014_x86_64 --only-binary=:all: -d .
pip download numpy==1.26.4 --python-version 3.10 --platform manylinux_2_17_x86_64 --only-binary=:all: -d .

REM Python 3.11
pip download numpy==1.26.4 --python-version 3.11 --platform manylinux2014_x86_64 --only-binary=:all: -d .
pip download numpy==1.26.4 --python-version 3.11 --platform manylinux_2_17_x86_64 --only-binary=:all: -d .

REM Python 3.12
pip download numpy==1.26.4 --python-version 3.12 --platform manylinux2014_x86_64 --only-binary=:all: -d .
pip download numpy==1.26.4 --python-version 3.12 --platform manylinux_2_17_x86_64 --only-binary=:all: -d .

echo.
echo Downloaded files:
dir /b *.whl

echo.
echo === DONE ===
echo Copy folder 'numpy_wheels' to offline machine
echo Then on offline machine:
echo   1. Check Python version: python --version
echo   2. Install matching wheel: pip install --no-index ./numpy_wheels/numpy-1.26.4-cp3XX-*.whl
pause
