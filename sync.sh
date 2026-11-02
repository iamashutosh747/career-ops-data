#!/usr/bin/env bash
# Commit and push all career-ops personal data. Safe to run repeatedly.
cd "$(dirname "$0")" || exit 0
git add -A
git diff --cached --quiet && exit 0
git commit -q -m "Auto-sync $(date -u +%Y-%m-%dT%H:%MZ)" || exit 0
git remote get-url origin >/dev/null 2>&1 || exit 0
for i in 1 2 3 4; do git push -q -u origin main && exit 0; sleep $((2**i)); done
echo "career-ops-data: push failed" >&2
