#!/bin/bash
set -e

# Antigravity Neo App Build & Package Script
# Builds the Swift app and packages it into a DMG installer.

echo "===================================================="
echo "🚀 Building Neo Desktop for macOS"
echo "===================================================="

# Ensure mise is in path for tuist
export PATH="$HOME/.mise/shims:$PATH"

# 1. Clean previous builds
echo "🧹 Cleaning up..."
rm -rf build_release
rm -f Neo.dmg

# 2. Generate Project
echo "🏗️ Generating project structure..."
mise exec -- tuist generate --no-open

# 3. Build Release
echo "⚙️ Compiling Release build..."
export TUIST_SKIP_UPDATE_CHECK=1
mise exec -- tuist xcodebuild build -scheme Neo -configuration Release -derivedDataPath build_release

# 4. Create DMG
echo "📦 Packaging DMG..."
APP_PATH="build_release/Build/Products/Release/Neo.app"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ Error: Neo.app not found at $APP_PATH"
    exit 1
fi

hdiutil create \
    -volname "Neo" \
    -srcfolder "$APP_PATH" \
    -ov -format UDZO \
    Neo.dmg

echo "===================================================="
echo "✔ Neo.dmg successfully built!"
echo "===================================================="
