#!/bin/sh

set -e

script_dir=$(dirname "$0")

# Change directory to the script's directory
cd "$script_dir" || exit
/usr/local/bin/python -u -m cfddns --config /app/config.json