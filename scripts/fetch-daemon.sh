#!/bin/sh
# Download the pinned mtga-tracker-daemon release into vendor/mtga-tracker-daemon/bin.
# The binaries are not committed to git; run this once after cloning.
set -eu

VERSION="1.0.11.0"
SHA256="fb087ff7b0be84b12677ee23726aadbd18998c81106ac16769c2206061ca176e"
URL="https://github.com/frcaton/mtga-tracker-daemon/releases/download/${VERSION}/mtga-tracker-daemon-Linux.tar.gz"
DEST="$(cd "$(dirname "$0")/.." && pwd)/vendor/mtga-tracker-daemon"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "Downloading mtga-tracker-daemon ${VERSION}..."
curl -fL -o "$tmp/daemon.tar.gz" "$URL"
echo "${SHA256}  $tmp/daemon.tar.gz" | sha256sum -c -
tar -xzf "$tmp/daemon.tar.gz" -C "$tmp" bin

rm -rf "$DEST/bin"
mkdir -p "$DEST"
mv "$tmp/bin" "$DEST/bin"
chmod +x "$DEST/bin/mtga-tracker-daemon"
echo "Installed to $DEST/bin"
