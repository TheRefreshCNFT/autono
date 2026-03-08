# Quick verification of Phase 1 fixes

Write-Host "`n🦭 Phase 1 Fixes Verification`n" -ForegroundColor Cyan

$files = @(
    "wallet-ui-interface/web-extension/src/popup/components/ReceiveModal.tsx",
    "wallet-ui-interface/web-extension/src/popup/components/ReceiveModal.css",
    "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.tsx",
    "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.css",
    "wallet-ui-interface/web-extension/src/popup/components/RecoveryImportModal.tsx",
    "wallet-ui-interface/web-extension/src/popup/components/RecoveryImportModal.css"
)

Write-Host "Checking new component files..." -ForegroundColor Yellow
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file" -ForegroundColor Red
    }
}

Write-Host "`nChecking code updates..." -ForegroundColor Yellow

$storeContent = Get-Content "wallet-ui-interface/web-extension/src/store/wallet.ts" -Raw
if ($storeContent -match "recoveryChallenge") {
    Write-Host "  ✓ Recovery challenge added to store" -ForegroundColor Green
} else {
    Write-Host "  ✗ Recovery challenge missing" -ForegroundColor Red
}

if ($storeContent -match "All 3 Chains Ready") {
    Write-Host "  ✓ Multi-chain wallet creation" -ForegroundColor Green
} else {
    Write-Host "  ✗ Multi-chain creation missing" -ForegroundColor Red
}

$appContent = Get-Content "wallet-ui-interface/web-extension/src/popup/App.tsx" -Raw
if ($appContent -match "ReceiveModal") {
    Write-Host "  ✓ ReceiveModal integrated" -ForegroundColor Green
} else {
    Write-Host "  ✗ ReceiveModal not integrated" -ForegroundColor Red
}

if ($appContent -match "feedwali") {
    Write-Host "  ✓ Branding updated to feedwali" -ForegroundColor Green
} else {
    Write-Host "  ✗ Branding not updated" -ForegroundColor Red
}

if ($appContent -notmatch '\$alice') {
    Write-Host "  ✓ No alice references" -ForegroundColor Green
} else {
    Write-Host "  ✗ alice still found" -ForegroundColor Red
}

Write-Host "`n✅ Verification complete!`n" -ForegroundColor Cyan
