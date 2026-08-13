#!/bin/sh
# Re-installs the pre-push hook. Git hooks live outside version control,
# so run this once after any fresh clone.
cd "$(dirname "$0")/.."
cp tools/pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
echo "pre-push hook installed"
