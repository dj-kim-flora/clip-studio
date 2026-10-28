#!/bin/bash
# Rebuild the on-device transcriber (needs macOS 26+ with the Speech framework's SpeechAnalyzer, and Xcode's swiftc).
set -e
cd "$(dirname "$0")"
swiftc -O -parse-as-library transcribe.swift -o transcribe.apple-bin
echo "built tools/transcribe.apple-bin (tools/transcribe uses it on macOS 26+)"
