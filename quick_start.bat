@echo off
:: Enhanced Quick Start Script with Error Handling
:: Fixed version that handles all common issues

echo ============================================================
echo Multimodal Vox Agent - Enhanced Quick Start
echo ============================================================
echo.

:: Set environment variable to fix OpenMP duplicate library issue
set KMP_DUPLICATE_LIB_OK=TRUE
echo [*] Fixed OpenMP library conflict

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11+ from python.org
    pause
    exit /b 1
)

echo [1/5] Testing project imports...
python test_imports.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Some imports failed!
    echo.
    echo Common solutions:
    echo 1. Install missing packages: pip install -r requirements.txt
    echo 2. Make sure you're in the correct directory
    echo 3. Check that Python 3.11+ is installed
    echo.
    pause
    exit /b 1
)

:: Check if LM Studio is running
echo.
echo [2/5] Checking LM Studio connection...
curl -s http://localhost:1234/v1/models >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Cannot connect to LM Studio!
    echo.
    echo Please:
    echo 1. Open LM Studio
    echo 2. Load a VLM model (qwen2-vl-2b-instruct recommended)
    echo 3. Go to Developer tab and click "Start Server"
    echo.
    echo Continue anyway? (Y/N)
    choice /c YN /n
    if errorlevel 2 exit /b 1
)
echo [OK] LM Studio check complete

:: Check dependencies
echo.
echo [3/5] Checking dependencies...
echo Do you want to install/update dependencies? (Y/N)
choice /c YN /n
if errorlevel 1 if not errorlevel 2 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [WARNING] Some packages failed to install
        echo The application might still work with missing optional features
    )
    echo.
)

:: Start the application
echo [4/5] Starting application...
echo.
echo Opening 2 terminal windows:
echo   1. Backend (FastAPI) - Port 8000
echo   2. Frontend (Streamlit) - Port 8501
echo.
echo Press any key to continue...
pause >nul

:: Start backend in new window with fixed environment
start "Backend - Multimodal Vox Agent" cmd /k "set KMP_DUPLICATE_LIB_OK=TRUE && echo Starting Backend... && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

:: Start frontend in new window with fixed environment
start "Frontend - Multimodal Vox Agent" cmd /k "set KMP_DUPLICATE_LIB_OK=TRUE && echo Starting Frontend... && streamlit run frontend/app.py"

echo.
echo [5/5] Application started!
echo.
echo ============================================================
echo Application Started Successfully!
echo ============================================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:8501
echo.
echo Your browser should open automatically in a few seconds.
echo.
echo To stop the application:
echo - Close the Backend and Frontend terminal windows
echo - Or press Ctrl+C in each window
echo.
echo Logs are in: app.log
echo.

:: Try to open browser
timeout /t 5 /nobreak >nul
start http://localhost:8501

echo All done! Enjoy your Multimodal Vox Agent!
echo.
pause
