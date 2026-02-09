@echo off
echo ============================================
echo   AI Auto Complete Server (GGUF/llama.cpp)
echo ============================================
echo.
echo Backend: llama-cpp-python
echo.

REM Check if llama-cpp-python is installed
pip show llama-cpp-python >nul 2>&1
if errorlevel 1 (
    echo Installing llama-cpp-python...
    pip install llama-cpp-python
)

python server_gguf.py

pause
