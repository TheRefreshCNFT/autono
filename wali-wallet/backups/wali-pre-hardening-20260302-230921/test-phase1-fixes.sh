#!/bin/bash
# Test script for Phase 1 critical fixes
# Run this to verify all changes are in place

echo "🦭 wAli Phase 1 Fixes - Verification Script"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} File exists: $1"
        ((passed++))
        return 0
    else
        echo -e "${RED}✗${NC} File missing: $1"
        ((failed++))
        return 1
    fi
}

# Function to check if string exists in file
check_string() {
    local file=$1
    local search=$2
    local description=$3
    
    if grep -q "$search" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $description"
        ((passed++))
        return 0
    else
        echo -e "${RED}✗${NC} $description (not found in $file)"
        ((failed++))
        return 1
    fi
}

# Function to check if string does NOT exist in file
check_not_exists() {
    local file=$1
    local search=$2
    local description=$3
    
    if ! grep -q "$search" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $description"
        ((passed++))
        return 0
    else
        echo -e "${RED}✗${NC} $description (still found in $file)"
        ((failed++))
        return 1
    fi
}

echo "Test 1: New Component Files"
echo "----------------------------"
check_file "wallet-ui-interface/web-extension/src/popup/components/ReceiveModal.tsx"
check_file "wallet-ui-interface/web-extension/src/popup/components/ReceiveModal.css"
check_file "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.tsx"
check_file "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.css"
check_file "wallet-ui-interface/web-extension/src/popup/components/RecoveryImportModal.tsx"
check_file "wallet-ui-interface/web-extension/src/popup/components/RecoveryImportModal.css"
echo ""

echo "Test 2: All 3 Wallets Created Simultaneously"
echo "---------------------------------------------"
check_string "wallet-ui-interface/web-extension/src/store/wallet.ts" \
    "chains: \['cardano', 'bitcoin', 'night'\]" \
    "Creates all 3 chains in createWallet()"
check_string "wallet-ui-interface/web-extension/src/store/wallet.ts" \
    "All 3 Chains Ready" \
    "Shows 'All 3 Chains Ready' message"
echo ""

echo "Test 3: Receive Modal Integration"
echo "----------------------------------"
check_string "wallet-ui-interface/web-extension/src/popup/App.tsx" \
    "import.*ReceiveModal" \
    "ReceiveModal imported in App.tsx"
check_string "wallet-ui-interface/web-extension/src/popup/App.tsx" \
    "showReceiveModal" \
    "Receive modal state tracking"
check_string "wallet-ui-interface/web-extension/src/popup/components/ReceiveModal.tsx" \
    "BTC.*CARDANO.*MIDNIGHT" \
    "3-chain tab selector in modal"
echo ""

echo "Test 4: Recovery Challenge Display"
echo "-----------------------------------"
check_string "wallet-ui-interface/web-extension/src/store/wallet.ts" \
    "recoveryChallenge" \
    "Recovery challenge state added to store"
check_string "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.tsx" \
    "Line 1.*Bot" \
    "4-line recovery format implemented"
check_string "wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.tsx" \
    "acknowledged" \
    "Mandatory acknowledgment checkbox"
echo ""

echo "Test 5: Recovery Import Flow"
echo "-----------------------------"
check_string "wallet-ui-interface/web-extension/src/popup/components/RecoveryImportModal.tsx" \
    "line1.*line2.*line3.*line4" \
    "4-line input form implemented"
check_string "wallet-ui-interface/web-extension/src/popup/App.tsx" \
    "showRecoveryImport" \
    "Recovery import modal state"
check_string "wallet-ui-interface/web-extension/src/store/wallet.ts" \
    "recoverFromNightChain" \
    "Recovery function added to store"
echo ""

echo "Test 6: Branding Update (\$alice → \$feedwali)"
echo "----------------------------------------------"
check_not_exists "wallet-ui-interface/web-extension/src/popup/App.tsx" \
    '\$alice' \
    "No \$alice in App.tsx"
check_not_exists "wallet-ui-interface/web-extension/src/popup/WaliApp.tsx" \
    '\$alice' \
    "No \$alice in WaliApp.tsx"
check_string "wallet-ui-interface/web-extension/src/popup/App.tsx" \
    '\$feedwali' \
    "\$feedwali used in App.tsx"
check_string "wallet-ui-interface/web-extension/README.md" \
    '\$feedwali' \
    "\$feedwali in web-extension README"
check_string "wallet-ui-interface/mobile-app/README.md" \
    '\$feedwali' \
    "\$feedwali in mobile-app README"
echo ""

echo "========================================"
echo "Test Results"
echo "========================================"
echo -e "${GREEN}Passed: $passed${NC}"
echo -e "${RED}Failed: $failed${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}🦭 All tests passed! Ready for Phase 1 beta!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some tests failed. Review the output above.${NC}"
    exit 1
fi
