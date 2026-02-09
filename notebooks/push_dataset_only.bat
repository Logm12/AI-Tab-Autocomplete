@echo off
REM Push only fim_dataset.jsonl

cd /d "%~dp0"

echo Building dataset-only image...
docker build -t longmac0110/ai-autocomplete-dataset:latest -f Dockerfile.dataset .

echo Pushing...
docker push longmac0110/ai-autocomplete-dataset:latest

echo.
echo Done! On offline machine:
echo   docker pull longmac0110/ai-autocomplete-dataset:latest
echo   docker create --name dataset_temp longmac0110/ai-autocomplete-dataset:latest
echo   docker cp dataset_temp:/data/fim_dataset.jsonl ./
echo   docker rm dataset_temp
pause
