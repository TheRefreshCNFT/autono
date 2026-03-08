@echo off
REM wAli Browser Extension Build Script (Windows)
REM Builds the production-ready extension with real wallet integration

echo 🦭 Building wAli Browser Extension...

REM Step 1: Install dependencies if needed
echo 📦 Checking dependencies...
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

REM Step 2: Build the extension
echo 🔨 Building extension...
call npm run build

REM Step 3: Verify build
if exist "dist\popup.js" (
    if exist "dist\background.js" (
        echo ✅ Build successful!
        echo.
        echo 📁 Extension built in: %CD%\dist
        echo.
        echo 🚀 To load in Chrome:
        echo    1. Open chrome://extensions/
        echo    2. Enable 'Developer mode'
        echo    3. Click 'Load unpacked'
        echo    4. Select the 'dist' folder
        echo.
        echo 🦭 wAli is ready!
        exit /b 0
    )
)

echo ❌ Build failed. Check errors above.
exit /b 1
