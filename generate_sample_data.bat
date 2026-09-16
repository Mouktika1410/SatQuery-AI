@echo off
echo ===================================================
echo  SatQuery - Generating Synthetic GeoTIFF Datasets
echo ===================================================
echo.

if exist "Backend\venv\Scripts\python.exe" (
    "Backend\venv\Scripts\python.exe" "scripts\create_synthetic_tifs.py"
) else (
    python "scripts\create_synthetic_tifs.py"
)

echo.
echo ===================================================
echo  Checking generated GeoTIFF files in data\input\:
echo ===================================================
dir "data\input\*.tif"
echo.
pause
