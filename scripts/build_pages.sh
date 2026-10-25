#!/bin/sh
# Build the static site for GitHub Pages: the web app playing the baked demo chat, plus the demo video.
#   scripts/build_pages.sh <outdir>
# Runs `npm --prefix web run build:static`, then copies web/dist, docs/demo.mp4 and an empty .nojekyll
# into <outdir>. The app uses relative URLs and no path routing, so it works under a subpath
# (https://<user>.github.io/<repo>/). With no API there, it plays demo.json and hides upload.
set -eu

if [ $# -ne 1 ]; then
  echo "usage: $0 <outdir>" >&2
  exit 2
fi

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$1

npm --prefix "$ROOT/web" run build:static

mkdir -p "$OUT"
cp -R "$ROOT/web/dist/." "$OUT/"
if [ -f "$ROOT/docs/demo.mp4" ]; then
  cp "$ROOT/docs/demo.mp4" "$OUT/demo.mp4"
else
  echo "warning: docs/demo.mp4 not found; the site will have no video" >&2
fi
: > "$OUT/.nojekyll"
# A static answer to the app's API probe, so the browser logs no 404: ok=false means "no API, play demo.json".
mkdir -p "$OUT/api"
printf '{"ok": false}\n' > "$OUT/api/health"
echo "site -> $OUT"
