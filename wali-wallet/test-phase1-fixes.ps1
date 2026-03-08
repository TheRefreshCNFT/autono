# Test script for Phase 1 critical fixes
# Run this to verify all changes are in place

Write-Host "🦭 wAli Phase 1 Fixes - Verification Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

# Function to check if file exists
function Test-FileExists {
    param($Path)
    if (Test-Path $Path) {
        Write-Host "✓ File exists: $Path" -ForegroundColor Green
        $script:passed++
        return $true
    }
    else {
        Write-Host "✗ File missing: $Path" -ForegroundColor Red
        $script:failed++
        return $false
    }
}

# Function to check if string exists in file
function Test-StringInFile {
    param($File, $Search, $Description)
    
    if (Test-Path $File) {
        $content = Get-Content $File -Raw -ErrorAction SilentlyContinue
        if ($content -match $Search) {
            Write-Host "✓ $Description" -ForegroundColor Green
            $script:passed++
            return $true
        }
        else {
            Write-Host "✗ $Description (not found in $File)" -ForegroundColor Red
            $script:failed++
            return $false
        }
    }
    else {
        Write-Host "✗ $Description (file not found: $File)" -ForegroundColor Red
        $script:failed++
        return $false
    }
}

# Function to check if string does NOT exist in file
function Test-StringNotInFile {
    param($File, $Search, $Description)
    
    if (Test-Path $File) {
        $content = Get-Content $File -Raw -ErrorAction SilentlyContinue
        if ($content -notmatch $Search) {
            Write-Host "✓ $Description" -ForegroundColor Green
            $script:passed++
            return $true
        }
        else {
            Write-Host "✗ $Description (still found in $File)" -ForegroundColor Red
            $script:failed++
            return $false
        }
    }
    else {
        Write-Host "✗ $Description (file not found: $File)" -ForegroundColor Yellow
        $script:failed++
        return $false
    }
}

Write-Host "Test 1: New Component Files" -ForegroundColor Yellow
Write-Host "----------------------------"
Test-FileExists "wallet-ui-interface/web-extension/src/popup/components/ReceiveModal.tsx"
Test-FileExists "wallet-ui-interface/web-extension/src/popup/components/ReceiveModal.css"
Test-FileExists "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.tsx"
Test-FileExists "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.css"
Test-FileExists "wallet-ui-interface/web-extension/src/popup/components/RecoveryImportModal.tsx"
Test-FileExists "wallet-ui-interface/web-extension/src/popup/components/RecoveryImportModal.css"
Write-Host ""

Write-Host "Test 2: All 3 Wallets Created Simultaneously" -ForegroundColor Yellow
Write-Host "---------------------------------------------"
Test-StringInFile "wallet-ui-interface/web-extension/src/store/wallet.ts" "chains: \['cardano', 'bitcoin', 'night'\]" "Creates all 3 chains in createWallet"
Test-StringInFile "wallet-ui-interface/web-extension/src/store/wallet.ts" "All 3 Chains Ready" "Shows 'All 3 Chains Ready' message"
Write-Host ""

Write-Host "Test 3: Receive Modal Integration" -ForegroundColor Yellow
Write-Host "----------------------------------"
Test-StringInFile "wallet-ui-interface/web-extension/src/popup/App.tsx" "import.*ReceiveModal" "ReceiveModal imported in App.tsx"
Test-StringInFile "wallet-ui-interface/web-extension/src/popup/App.tsx" "showReceiveModal" "Receive modal state tracking"
Test-StringInFile "wallet-ui-interface/web-extension/src/popup/components/ReceiveModal.tsx" "BTC.*CARDANO.*MIDNIGHT" "3-chain tab selector in modal"
Write-Host ""

Write-Host "Test 4: Recovery Challenge Display" -ForegroundColor Yellow
Write-Host "-----------------------------------"
Test-StringInFile "wallet-ui-interface/web-extension/src/store/wallet.ts" "recoveryChallenge" "Recovery challenge state added to store"
Test-StringInFile "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.tsx" "Line 1.*Bot" "4-line recovery format implemented"
Test-StringInFile "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.tsx" "acknowledged" "Mandatory acknowledgment checkbox"
Write-Host ""

Write-Host "Test 5: Recovery Import Flow" -ForegroundColor Yellow
Write-Host "-----------------------------"
Test-StringInFile "wallet-ui-interface/web-extension/src/popup/components/RecoveryImportModal.tsx" "line1.*line2.*line3.*line4" "4-line input form implemented"
Test-StringInFile "wallet-ui-interface/web-extension/src/popup/App.tsx" "showRecoveryImport" "Recovery import modal state"
Test-StringInFile "wallet-ui-interface/web-extension/src/store/wallet.ts" "recoverFromNightChain" "Recovery function added to store"
Write-Host ""

Write-Host "Test 6: Branding Update" -ForegroundColor Yellow
Write-Host "----------------------------------------------"
Test-StringNotInFile "wallet-ui-interface/web-extension/src/popup/App.tsx" 'alice' "No alice in App.tsx"
Test-StringNotInFile "wallet-ui-interface/web-extension/src/popup/WaliApp.tsx" 'alice' "No alice in WaliApp.tsx"
Test-StringInFile "wallet-ui-interface/web-extension/src/popup/App.tsx" 'feedwali' "feedwali used in App.tsx"
Test-StringInFile "wallet-ui-interface/web-extension/README.md" 'feedwali' "feedwali in web-extension README"
Test-StringInFile "wallet-ui-interface/mobile-app/README.md" 'feedwali' "feedwali in mobile-app README"
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Results" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red
Write-Host ""

if ($failed -eq 0) {
    Write-Host "🦭 All tests passed! Ready for Phase 1 beta!" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "⚠️  Some tests failed. Review the output above." -ForegroundColor Yellow
    exit 1
}
