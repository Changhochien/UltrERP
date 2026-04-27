#!/bin/bash
#
# i18n Pre-commit Hook
# 
# This script runs i18n validation before commits.
# Install by copying to .git/hooks/pre-commit or using Husky.
#
# Usage:
#   ./scripts/i18n-pre-commit.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "🔍 i18n Pre-commit Validation"
echo "=============================="

# Check if locale files were modified
LOCALE_CHANGES=$(git diff --cached --name-only | grep -E "public/locales|src/lib/i18n" || true)

if [ -z "$LOCALE_CHANGES" ]; then
  echo "✅ No i18n files changed, skipping validation."
  exit 0
fi

echo "📝 i18n files changed:"
echo "$LOCALE_CHANGES" | while read -r file; do
  echo "  - $file"
done
echo ""

# Check for required tools
if ! command -v node &> /dev/null; then
  echo -e "${YELLOW}⚠️  Node.js not found, skipping i18n validation${NC}"
  exit 0
fi

# Run validation
ERRORS=0
WARNINGS=0

echo "📋 Running validation checks..."
echo ""

# Check 1: Locale parity
echo "  [1/3] Checking locale parity..."
if node -e "
const { execSync } = require('child_process');
try {
  execSync('npx tsx scripts/i18n-check.ts', { stdio: 'pipe' });
} catch (e) {
  process.exit(e.status || 1);
}
"; then
  echo -e "  ${GREEN}✓${NC} Locale parity check passed"
else
  echo -e "  ${RED}✗${NC} Locale parity check failed"
  ERRORS=$((ERRORS + 1))
fi

# Check 2: Type generation
echo "  [2/3] Generating i18n types..."
if npx tsx scripts/generate-i18n-types.ts > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} Type generation successful"
else
  echo -e "  ${RED}✗${NC} Type generation failed"
  ERRORS=$((ERRORS + 1))
fi

# Check 3: Coverage
echo "  [3/3] Checking translation coverage..."
COVERAGE=$(npx tsx scripts/i18n-coverage.ts 2>/dev/null | grep "zh-Hant" | awk '{print $3}' | sed 's/%//')
if [ -n "$COVERAGE" ] && [ "$COVERAGE" -ge 95 ]; then
  echo -e "  ${GREEN}✓${NC} Coverage: ${COVERAGE}%"
elif [ -n "$COVERAGE" ]; then
  echo -e "  ${YELLOW}⚠${NC} Coverage below threshold: ${COVERAGE}% (threshold: 95%)"
  WARNINGS=$((WARNINGS + 1))
else
  echo -e "  ${YELLOW}⚠${NC} Could not determine coverage"
  WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "=============================="

if [ $ERRORS -gt 0 ]; then
  echo -e "${RED}❌ i18n validation failed with $ERRORS error(s)${NC}"
  echo ""
  echo "Please fix the issues before committing."
  echo "Run 'npx tsx scripts/i18n-validate.ts' for details."
  exit 1
fi

if [ $WARNINGS -gt 0 ]; then
  echo -e "${YELLOW}⚠️  i18n validation completed with $WARNINGS warning(s)${NC}"
  echo ""
  echo "Commit will proceed but please address warnings."
fi

echo -e "${GREEN}✅ i18n validation passed${NC}"
echo ""

exit 0
