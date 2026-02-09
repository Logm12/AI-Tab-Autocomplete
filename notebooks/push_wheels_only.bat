@echo off
REM Build and push wheels-only image for Python 3.11

cd /d "%~dp0"

echo === Building Wheels Image (Python 3.11) ===
docker build -t longmac0110/ai-autocomplete-wheels:py311 -f Dockerfile.wheels .

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo === Pushing to Docker Hub ===
docker push longmac0110/ai-autocomplete-wheels:py311

echo.
echo === DONE ===
echo.
echo On offline machine:
echo   docker pull longmac0110/ai-autocomplete-wheels:py311
echo   docker create --name wheels_temp longmac0110/ai-autocomplete-wheels:py311
echo   docker cp wheels_temp:/wheels/. ./wheels/
echo   docker rm wheels_temp
echo   pip install --no-index --find-links=./wheels numpy==1.26.4
pause
