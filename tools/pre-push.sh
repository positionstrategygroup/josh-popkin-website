#!/bin/sh
# Block any push that would put a broken page on joshpopkin.com.
echo "Running site checks before push..."
python3 tools/check.py || {
  echo ""
  echo "PUSH BLOCKED — fix the failures above, or bypass with: git push --no-verify"
  exit 1
}
