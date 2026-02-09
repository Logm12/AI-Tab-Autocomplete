@echo off
REM =====================================================
REM Build and Push Training Package Image
REM =====================================================

echo === Building AI Auto-Complete Training Package ===
echo.

cd /d "%~dp0"

echo Step 1: Building Docker image...
docker build -t longmac0110/ai-autocomplete-training:latest -f Dockerfile.training .

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker build failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Pushing to Docker Hub...
docker push longmac0110/ai-autocomplete-training:latest

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker push failed!
    echo Make sure you are logged in: docker login
    pause
    exit /b 1
)

echo.
echo === SUCCESS! ===
echo Image pushed to: longmac0110/ai-autocomplete-training:latest
echo.
echo On offline machine, run:
echo   docker pull longmac0110/ai-autocomplete-training:latest
echo   docker run --rm -v $(pwd)/training_package:/output longmac0110/ai-autocomplete-training cp -r /package/* /output/
echo.
pause
