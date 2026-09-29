#!/usr/bin/env bash
# Deploy the chatbot in app/ to the HuggingFace Space.
# Usage: ./deploy-space.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPACE_ID="Akivakauf/Career_Agent"
SPACE_DIR="${SPACE_DIR:-$HOME/portfolio/career-agent-space}"

if [ ! -d "$SPACE_DIR/.git" ]; then
  echo "Cloning Space to $SPACE_DIR ..."
  git clone "https://huggingface.co/spaces/$SPACE_ID" "$SPACE_DIR"
fi

cd "$SPACE_DIR"
git pull --ff-only

rsync -a --delete \
  --exclude '.git' --exclude '.gitattributes' --exclude '__pycache__' \
  "$REPO_DIR/app/" .

git add -A
if git diff --cached --quiet; then
  echo "No changes to deploy."
  exit 0
fi

git commit -m "Deploy chatbot update"
HF_TOKEN=$(grep '^HF_TOKEN=' "$REPO_DIR/.env" | cut -d'=' -f2-)
git push "https://Akivakauf:${HF_TOKEN}@huggingface.co/spaces/$SPACE_ID" HEAD:main
echo "Pushed - the Space will rebuild automatically."
