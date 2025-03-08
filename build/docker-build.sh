#!/bin/bash

# Directory of this script
SCRIPT_DIR=$(dirname "$(realpath "$0")")

VERSION_FILE="$SCRIPT_DIR/../cfddns/__about__.py"

if [[ ! -f "$VERSION_FILE" ]]; then
  echo "Version file not found: $VERSION_FILE"
  exit 1
fi

VERSION=$(awk -F'[()]' '/__version_info__/ {if (NF>1) {gsub(/[^0-9,]/, "", $2); gsub(/,/, ".", $2); print $2}}' "$VERSION_FILE")

REPO="j3br/cfddns"

# Build image with module version number and 'latest' tags
docker build -t "$REPO:$VERSION" -t "$REPO:latest" "$SCRIPT_DIR/../"
