@echo off
REM YT-to-Shorts — One-Command Setup (Windows)
REM Run: setup.bat
REM Installs everything needed to run the pipeline.

echo.
echo ============================================
echo   YT-to-Shorts — Automatic Setup (Windows)
echo ============================================
echo.

set ERRORS=0
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ─────────────────────────────────────────────
REM 1. Python 3
REM ─────────────────────────────────────────────
echo Checking Python 3...
python3 --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2" %%v in ('python3 --version 2^>^&1') do echo   [OK] Python %%v
    set "PY=python3"
    goto :check_pip
)
python --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   [OK] Python %%v
    set "PY=python"
    goto :check_pip
)
echo   [INSTALLING] Python 3...
winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] Python 3 installed — RESTART this Command Prompt and run setup.bat again
    set /a ERRORS+=1
    goto :check_pip
) else (
    echo   [MISSING] Python 3 — download from https://python.org/downloads
    echo            IMPORTANT: Check "Add Python to PATH" during install
    set /a ERRORS+=1
    set "PY=python3"
)
:check_pip
echo.

REM ─────────────────────────────────────────────
REM 2. pip
REM ─────────────────────────────────────────────
echo Checking pip...
%PY% -m pip --version >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] pip available
) else (
    echo   [INSTALLING] pip...
    %PY% -m ensurepip --upgrade >nul 2>&1
    %PY% -m pip --version >nul 2>&1
    if %errorlevel%==0 (
        echo   [OK] pip installed
    ) else (
        echo   [MISSING] pip — try: %PY% -m ensurepip --upgrade
        set /a ERRORS+=1
    )
)
echo.

REM ─────────────────────────────────────────────
REM 3. FFmpeg
REM ─────────────────────────────────────────────
echo Checking FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] ffmpeg available
    goto :check_ffprobe
)
echo   [INSTALLING] FFmpeg via winget...
winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] FFmpeg installed — you may need to RESTART Command Prompt
) else (
    echo   [MISSING] FFmpeg — install manually:
    echo            winget install Gyan.FFmpeg
    echo            OR download from https://www.gyan.dev/ffmpeg/builds/
    echo            Extract to C:\ffmpeg and add C:\ffmpeg\bin to PATH
    set /a ERRORS+=1
)
:check_ffprobe
echo.

REM ─────────────────────────────────────────────
REM 4. ffprobe
REM ─────────────────────────────────────────────
echo Checking ffprobe...
ffprobe -version >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] ffprobe available
) else (
    echo   [MISSING] ffprobe — comes with FFmpeg. Reinstall FFmpeg.
    set /a ERRORS+=1
)
echo.

REM ─────────────────────────────────────────────
REM 5. yt-dlp
REM ─────────────────────────────────────────────
echo Checking yt-dlp...
yt-dlp --version >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] yt-dlp available
    goto :install_packages
)
echo   [INSTALLING] yt-dlp...
winget install yt-dlp.yt-dlp --accept-source-agreements --accept-package-agreements >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] yt-dlp installed via winget
    goto :install_packages
)
%PY% -m pip install yt-dlp >nul 2>&1
yt-dlp --version >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] yt-dlp installed via pip
) else (
    echo   [MISSING] yt-dlp — try: pip install yt-dlp
    set /a ERRORS+=1
)
:install_packages
echo.

REM ─────────────────────────────────────────────
REM 6. Python packages (requirements.txt)
REM ─────────────────────────────────────────────
echo Installing Python packages...
if exist requirements.txt (
    %PY% -m pip install -r requirements.txt >nul 2>&1

    %PY% -c "import cv2" >nul 2>&1
    if %errorlevel%==0 (echo   [OK] opencv-python) else (echo   [MISSING] opencv-python & set /a ERRORS+=1)

    %PY% -c "import numpy" >nul 2>&1
    if %errorlevel%==0 (echo   [OK] numpy) else (echo   [MISSING] numpy & set /a ERRORS+=1)

    %PY% -c "import PIL" >nul 2>&1
    if %errorlevel%==0 (echo   [OK] Pillow) else (echo   [MISSING] Pillow & set /a ERRORS+=1)

    %PY% -c "import yt_dlp" >nul 2>&1
    if %errorlevel%==0 (echo   [OK] yt-dlp python package) else (echo   [MISSING] yt-dlp python package & set /a ERRORS+=1)
) else (
    echo   [MISSING] requirements.txt — make sure you're in the yt-to-shorts folder
    set /a ERRORS+=1
)
echo.

REM ─────────────────────────────────────────────
REM 7. Fonts
REM ─────────────────────────────────────────────
echo Checking fonts...
if exist fonts\Montserrat-Bold.ttf (
    if exist fonts\Montserrat-ExtraBold.ttf (
        echo   [OK] Montserrat fonts (Bold + ExtraBold)
    ) else (
        echo   [MISSING] Montserrat-ExtraBold.ttf — re-extract the ZIP
        set /a ERRORS+=1
    )
) else (
    echo   [MISSING] Montserrat fonts — re-extract the ZIP
    set /a ERRORS+=1
)
echo.

REM ─────────────────────────────────────────────
REM 8. .env file
REM ─────────────────────────────────────────────
echo Checking .env configuration...
if exist .env (
    findstr /c:"GATHOS_IMAGE_API_KEY=img_" .env >nul 2>&1
    if %errorlevel%==0 (
        echo   [OK] .env file with API key configured
    ) else (
        echo   [MISSING] .env exists but API key is empty
        echo            Edit .env and add your Gathos Image API key
        echo            Get one at: https://gathos.com
        set /a ERRORS+=1
    )
) else (
    if exist .env.example (
        copy .env.example .env >nul
        echo   [CREATED] .env file from template
        echo   [ACTION NEEDED] Edit .env and add your Gathos Image API key
        echo            Get one at: https://gathos.com
        set /a ERRORS+=1
    ) else (
        echo   [MISSING] .env.example — make sure you're in the yt-to-shorts folder
        set /a ERRORS+=1
    )
)
echo.

REM ─────────────────────────────────────────────
REM Summary
REM ─────────────────────────────────────────────
echo ============================================
if %ERRORS%==0 (
    echo   ALL DONE! Setup complete.
    echo.
    echo   To verify:  set PYTHONPATH=. ^&^& %PY% lib/pipeline.py --stage check
    echo.
    echo   To run:     Open Claude Code in this folder and say:
    echo              "Make me 5 clips from this YouTube video: [URL]"
) else (
    echo   %ERRORS% issue(s) need attention.
    echo   Fix the items marked [MISSING] above, then run setup.bat again.
    echo.
    echo   If you just installed Python or FFmpeg, RESTART Command Prompt
    echo   and run setup.bat again — new installs need a fresh terminal.
)
echo ============================================
echo.
pause
