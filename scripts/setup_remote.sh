#!/usr/bin/env bash
# Re-attach this workspace's git identity and GitHub remote.
#
# The sandbox does not persist .git/config (it is excluded as a credential path),
# so the remote and identity are lost on every recycle. Run this once per session:
#
#   bash scripts/setup_remote.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
REPO="${1:-git@github.com:syedali17a-del/Crimenet_ai.git}"
git config user.name  "CrimeNet AI"
git config user.email "crimenet-ai@users.noreply.github.com"
# The sandbox drops the executable bit between sessions; the repo already records 100755.
git config core.fileMode false
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO"
echo "remote: $(git remote get-url origin)"
echo "branch: $(git branch --show-current) at $(git rev-parse --short HEAD) — $(git log -1 --format=%s)"
echo "history: $(git rev-list --count HEAD) commit(s), $(git ls-files | wc -l) tracked files"
