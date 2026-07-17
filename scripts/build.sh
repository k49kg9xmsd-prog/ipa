#!/usr/bin/env bash
set -euo pipefail
REQ_DIR="$1"
OUT_DIR="${2:-output}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$REQ_DIR/config.json"
APP_NAME=$(jq -r '.appName' "$CFG")
IPA_NAME=$(jq -r '.ipaName' "$CFG" | sed 's/[^A-Za-z0-9._-]/-/g')
BUNDLE_ID=$(jq -r '.bundleId' "$CFG")
VERSION=$(jq -r '.version' "$CFG")
BUILD=$(jq -r '.build' "$CFG")
MIN_IOS=$(jq -r '.minIos' "$CFG")
BUILD_DIR="$ROOT/.build/$IPA_NAME"
APP_DIR="$BUILD_DIR/Payload/$APP_NAME.app"
rm -rf "$BUILD_DIR" "$OUT_DIR" && mkdir -p "$APP_DIR" "$OUT_DIR"

python3 "$ROOT/scripts/generate.py" "$CFG" "$REQ_DIR" "$APP_DIR"
SDK=$(xcrun --sdk iphoneos --show-sdk-path)
xcrun swiftc "$BUILD_DIR/App.swift" -o "$APP_DIR/$APP_NAME" \
  -sdk "$SDK" -target "arm64-apple-ios${MIN_IOS}" -parse-as-library \
  -framework UIKit -framework WebKit -framework UniformTypeIdentifiers \
  -Xlinker -rpath -Xlinker @executable_path/Frameworks
chmod +x "$APP_DIR/$APP_NAME"

ICON=$(find "$REQ_DIR" -maxdepth 1 -type f -iname 'icon.*' | head -n1)
mkdir -p "$BUILD_DIR/AppIcon.appiconset"
python3 "$ROOT/scripts/icons.py" "$ICON" "$BUILD_DIR/AppIcon.appiconset"
cat > "$BUILD_DIR/Assets.xcassets/Contents.json" <<'JSON'
{"info":{"author":"xcode","version":1}}
JSON
mv "$BUILD_DIR/AppIcon.appiconset" "$BUILD_DIR/Assets.xcassets/"
xcrun actool "$BUILD_DIR/Assets.xcassets" --compile "$APP_DIR" --platform iphoneos \
  --minimum-deployment-target "$MIN_IOS" --app-icon AppIcon --output-partial-info-plist "$BUILD_DIR/asset-info.plist" >/dev/null

plutil -replace CFBundleExecutable -string "$APP_NAME" "$APP_DIR/Info.plist"
plutil -replace CFBundleIdentifier -string "$BUNDLE_ID" "$APP_DIR/Info.plist"
plutil -replace CFBundleShortVersionString -string "$VERSION" "$APP_DIR/Info.plist"
plutil -replace CFBundleVersion -string "$BUILD" "$APP_DIR/Info.plist"
plutil -replace MinimumOSVersion -string "$MIN_IOS" "$APP_DIR/Info.plist"

cd "$BUILD_DIR"
/usr/bin/zip -qry "$ROOT/$OUT_DIR/$IPA_NAME.ipa" Payload
shasum -a 256 "$ROOT/$OUT_DIR/$IPA_NAME.ipa" > "$ROOT/$OUT_DIR/$IPA_NAME.ipa.sha256"
echo "Built: $ROOT/$OUT_DIR/$IPA_NAME.ipa"
