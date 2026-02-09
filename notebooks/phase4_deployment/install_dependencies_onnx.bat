@echo off
echo Installing dependencies for AI Auto-Complete Server...
pip install fastapi uvicorn optimum[onnxruntime] transformers torch pydantic
echo.
echo Installation complete.
pause
