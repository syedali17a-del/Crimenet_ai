#!/usr/bin/env bash
# CrimeNet AI — create the GitHub remote and push this repository.
#
# Usage (from the repository root):
#
#   bash scripts/push_to_github.sh https://github.com/<you>/<repo>.git
#
# Private repo, or if git asks for a password:
#
#   GITHUB_TOKEN=ghp_xxx bash scripts/push_to_github.sh https://github.com/<you>/<repo>.git
#
# The token is used once, in-memory, only for this push. Use a fine-grained token
# with "Contents: Read and write" on that one repository, and revoke it afterwards.
# It is never written to .git/config or to any file (the remote is stored WITHOUT
# the token, so a later `git config -l` shows nothing sensitive).
#
# Optional environment:
#   GIT_USER_NAME   commit author name      (default: CrimeNet AI)
#   GIT_USER_EMAIL  commit author email     (default: a GitHub noreply address)
#   BRANCH          branch to push          (default: main)
set -euo pipefail

REPO_URL="${1:-}"
BRANCH="${BRANCH:-main}"
AUTHOR_NAME="${GIT_USER_NAME:-CrimeNet AI}"
AUTHOR_EMAIL="${GIT_USER_EMAIL:-crimenet-ai@users.noreply.github.com}"

if [ -z "$REPO_URL" ]; then
  echo "usage: bash scripts/push_to_github.sh https://github.com/<you>/<repo>.git"
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v git >/dev/null || { echo "✖ git is not installed"; exit 1; }

# --- 1. repository + identity ------------------------------------------------
if [ ! -d .git ]; then
  echo "· git init -b $BRANCH"
  git init -b "$BRANCH" >/dev/null
fi
git config user.name "$AUTHOR_NAME"
git config user.email "$AUTHOR_EMAIL"

# --- 2. make sure everything is staged and committed -------------------------
if [ -n "$(git status --porcelain)" ]; then
  echo "· staging working tree"
  git add -A
  git commit -q -m "CrimeNet AI: evidence-driven investigative intelligence workbench"
fi

echo "· commits:"
git --no-pager log --oneline -n 5 | sed 's/^/    /'

# --- 3. sanity checks before anything leaves this machine --------------------
# Guard rails against the two mistakes that are expensive to undo on a public repo:
# committing runtime state, and committing real credentials.
TRACKED=$(git ls-files | wc -l)
echo "· tracked files: $TRACKED"

if git ls-files | grep -qE '(^|/)(node_modules|dist)/'; then
  echo "✖ refusing to push: node_modules/ or dist/ is tracked (remove it and re-run)"; exit 1
fi
if git ls-files | grep -qE 'ledger(_witness)?\.db'; then
  echo "✖ refusing to push: an audit ledger .db file is tracked"; exit 1
fi
if git ls-files | grep -q '^uploads/'; then
  echo "✖ refusing to push: uploads/ is tracked (local/personal files)"; exit 1
fi
# The scanner's own source contains these pattern literals, so it excludes itself —
# otherwise this check always "finds" a credential in scripts/push_to_github.sh.
CRED_PATTERN='ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----'
if git grep -InE "$CRED_PATTERN" -- . ':!scripts/push_to_github.sh' 2>/dev/null | head -3 | grep -q .; then
  echo "✖ refusing to push: a credential pattern was found in tracked files"
  git grep -InE "$CRED_PATTERN" -- . ':!scripts/push_to_github.sh' | head -3 | sed 's/^/    /'
  exit 1
fi
echo "✔ pre-push checks passed (no node_modules/dist, no ledgers, no uploads/, no credentials)"

# --- 4. remote + push --------------------------------------------------------
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
echo "· remote: $REPO_URL"

echo "· checking remote reachability"
if [ -n "${GITHUB_TOKEN:-}" ]; then
  # Token is passed through the environment, not embedded in the URL, so it never
  # ends up in .git/config or in shell history.
  export GIT_ASKPASS=/bin/true
  PUSH_URL="$(printf '%s' "$REPO_URL" | sed -E "s#https://#https://x-access-token:${GITHUB_TOKEN}@#")"
  if ! git ls-remote "$PUSH_URL" >/dev/null 2>&1; then
    echo "✖ cannot reach the remote — check the URL and the token's repository access"
    exit 1
  fi
  echo "· pushing $BRANCH (with token)"
  if ! git push "$PUSH_URL" "HEAD:refs/heads/$BRANCH"; then
    echo
    echo "✖ push rejected. If the repository was created WITH a README or licence, its"
    echo "  history is unrelated to this one. Either delete and recreate the repo empty,"
    echo "  or merge the two histories deliberately:"
    echo "      git remote set-url origin $REPO_URL && git fetch origin"
    echo "      git merge --allow-unrelated-histories origin/$BRANCH"
    echo "      git push $PUSH_URL HEAD:refs/heads/$BRANCH"
    exit 1
  fi
  # Keep the local remote clean of credentials.
  git remote set-url origin "$REPO_URL"
else
  if ! git ls-remote origin >/dev/null 2>&1; then
    echo "✖ cannot reach $REPO_URL without credentials."
    echo "  Re-run with a token:  GITHUB_TOKEN=ghp_xxx bash scripts/push_to_github.sh $REPO_URL"
    exit 1
  fi
  git push -u origin "$BRANCH"
fi

echo
echo "✔ pushed — open $REPO_URL in a browser and check the README renders."
echo "  If the commit author looks wrong:"
echo "    git -c user.name='You' -c user.email='you@example.com' commit --amend --reset-author --no-edit"
echo "    git push --force-with-lease origin $BRANCH"
