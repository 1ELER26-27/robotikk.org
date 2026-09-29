#!/usr/bin/env bash
# Kjøres av webhook-tjenesten (som robotikk-brukeren) etter push til main.
set -euo pipefail

REPO_DIR="/opt/robotikk-site"
cd "$REPO_DIR"

git pull --ff-only origin main

# Bygg til en midlertidig mappe i samme filsystem, så byttet blir atomisk.
BUILD_TMP="$(mktemp -d "$REPO_DIR/.build-XXXXXX")"
trap 'rm -rf "$BUILD_TMP"' EXIT

hugo --minify --destination "$BUILD_TMP"
chmod -R o+rX "$BUILD_TMP"

rm -rf "$REPO_DIR/public.old"
[ -d "$REPO_DIR/public" ] && mv "$REPO_DIR/public" "$REPO_DIR/public.old"
mv "$BUILD_TMP" "$REPO_DIR/public"
rm -rf "$REPO_DIR/public.old"

echo "Deploy fullført: $(date -u +%FT%TZ)"
