#!/bin/bash

# Directory of this script
SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Path to the version file
VERSION_FILE="$SCRIPT_DIR/../cfddns/__init__.py"

get_current_version() {
    grep '__version__' "$VERSION_FILE" | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+'
}

update_version() {
    local new_version=$1
    sed -i '' -E "s/__version__ = \"[0-9]+\.[0-9]+\.[0-9]+\"/__version__ = \"$new_version\"/" "$VERSION_FILE"
}

current_version=$(get_current_version)

# Split the version into major, minor, and patch
IFS='.' read -r major minor patch <<< "$current_version"

# Bump the version based on the argument
case $1 in
    major)
        ((major++))
        minor=0
        patch=0
        ;;
    minor)
        ((minor++))
        patch=0
        ;;
    patch)
        ((patch++))
        ;;
    *)
        echo "Usage: $0 {major|minor|patch}"
        exit 1
        ;;
esac

new_version="$major.$minor.$patch"
update_version "$new_version"

echo "Version bumped to $new_version"
