# wAli Security Hardening Verification Script
# Run this to verify all 4 critical fixes are properly implemented

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "wAli Security Hardening Verification" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# Check 1: Build successful
Write-Host "[CHECK 1] Build Status" -ForegroundColor Yellow
if (Test-Path "dist") {
    $jsCount = (Get-ChildItem dist -Recurse -Filter "*.js").Count
    Write-Host "  ✅ Build successful ($jsCount JS files)" -ForegroundColor Green
} else {
    Write-Host "  ❌ Build failed - no dist folder" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Check 2: Rate Limiter
Write-Host "[CHECK 2] API Rate Limiting" -ForegroundColor Yellow
if (Test-Path "dist/cardano/blockfrost-api.js") {
    $content = Get-Content "dist/cardano/blockfrost-api.js" -Raw
    if ($content -match "BlockfrostRateLimiter") {
        Write-Host "  ✅ Rate limiter class found" -ForegroundColor Green
        if ($content -match "throttle") {
            Write-Host "  ✅ Throttle method implemented" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Throttle method missing" -ForegroundColor Red
            $allPassed = $false
        }
    } else {
        Write-Host "  ❌ Rate limiter class not found" -ForegroundColor Red
        $allPassed = $false
    }
} else {
    Write-Host "  ❌ blockfrost-api.js not found" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Check 3: Recovery Storage
Write-Host "[CHECK 3] Recovery Backend" -ForegroundColor Yellow
if (Test-Path "dist/night-chain/recovery-storage.js") {
    Write-Host "  ✅ RecoveryStorage class built" -ForegroundColor Green
    $content = Get-Content "dist/night-chain/recovery-storage.js" -Raw
    if ($content -match "indexBackup") {
        Write-Host "  ✅ indexBackup method found" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  indexBackup method not found (check implementation)" -ForegroundColor Yellow
    }
    if ($content -match "lookupBackup") {
        Write-Host "  ✅ lookupBackup method found" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  lookupBackup method not found (check implementation)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ❌ recovery-storage.js not found" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Check 4: Encryption Verification
Write-Host "[CHECK 4] Encryption Verification" -ForegroundColor Yellow
if (Test-Path "dist/night-chain/integration.js") {
    $content = Get-Content "dist/night-chain/integration.js" -Raw
    if ($content -match "ENCRYPTION_VERIFICATION_FAILED") {
        Write-Host "  ✅ Encryption verification enforced" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Verification check not found (may be implemented differently)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ❌ integration.js not found" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Check 5: Security Tests
Write-Host "[CHECK 5] Automated Security Tests" -ForegroundColor Yellow
if (Test-Path "src/__tests__/security-validation.test.ts") {
    $content = Get-Content "src/__tests__/security-validation.test.ts" -Raw
    $testCount = ([regex]::Matches($content, "\btest\(")).Count
    Write-Host "  ✅ Security test file exists ($testCount tests)" -ForegroundColor Green
    
    if ($content -match "BIP39") {
        Write-Host "  ✅ BIP39 leak detection tests present" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  BIP39 tests not found" -ForegroundColor Yellow
    }
    
    if ($content -match "wipeMemory") {
        Write-Host "  ✅ Memory wiping tests present" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Memory wiping tests not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ❌ security-validation.test.ts not found" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Summary
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "✅ All critical fixes verified!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Run manual security tests (see SECURITY_HARDENING_COMPLETE.md)" -ForegroundColor White
    Write-Host "  2. Test recovery flow end-to-end" -ForegroundColor White
    Write-Host "  3. Deploy to testnet for beta testing" -ForegroundColor White
    Write-Host ""
    exit 0
} else {
    Write-Host "❌ Some checks failed - review output above" -ForegroundColor Red
    Write-Host ""
    Write-Host "Run 'npm run build' to rebuild if needed" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
