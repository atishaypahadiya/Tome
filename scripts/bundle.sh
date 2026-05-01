#!/usr/bin/env bash
# Builds the visualizer and copies the output into the Python package bundle.
# Run this whenever you change anything under visualizer/src/.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_DIR="$REPO_ROOT/visualizer"
DEST_DIR="$REPO_ROOT/tome/_bundled/visualizer"

echo "==> Building visualizer..."
(cd "$SRC_DIR" && npm run build)

echo "==> Copying dist/ -> tome/_bundled/visualizer/"
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"
cp -R "$SRC_DIR/dist/." "$DEST_DIR/"

echo "==> Done. Don't forget to commit the changes under tome/_bundled/visualizer/"
