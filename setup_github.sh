#!/usr/bin/env bash
# One-time setup: authenticate gh, create the public repo, fix up the
# ShadowMountPlus mirror URL now that the repo name is known, and push.
#
# Run this yourself (Claude Code's auto-mode blocks it from creating public
# GitHub repos / OAuth grants on your behalf): from this directory, run
#   bash setup_github.sh
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
REPO_NAME="${1:-ps5-custom-payloads}"

if ! gh auth status >/dev/null 2>&1; then
  echo "Logging into GitHub CLI (opens a browser)..."
  gh auth login --hostname github.com --git-protocol https --web
fi

if ! gh repo view "$REPO_NAME" >/dev/null 2>&1; then
  echo "Creating public repo $REPO_NAME..."
  gh repo create "$REPO_NAME" --public --source=. --remote=origin
else
  git remote add origin "https://github.com/$(gh api user -q .login)/$REPO_NAME.git" 2>/dev/null || true
fi

SLUG=$(gh repo view "$REPO_NAME" --json nameWithOwner -q .nameWithOwner)
echo "Repo: https://github.com/$SLUG"

echo "Regenerating payloads.json with the real mirror URL..."
GITHUB_REPOSITORY="$SLUG" python3 scripts/update_payloads.py

git add -A
git commit -m "Set real repo URL for mirrored payloads" --allow-empty -q
git branch -M main
git push -u origin main

echo
echo "Done. Add this source URL in Payload Manager:"
echo "  https://raw.githubusercontent.com/$SLUG/main/payloads.json"
echo
echo "Enable Actions on the repo (Settings > Actions > allow) so the 6-hourly"
echo "auto-update workflow can run and push updates."
