#!/bin/sh

set -e

script_dir=$(dirname "$0")

echo "Starting container..."

# Check if the configuration file exists in the expected location
if ! [[ -f "$script_dir/config.yaml" ]]; then
  echo "ERROR: Config file not found. Make sure it's mounted as a volume using:"
  echo "  volumes:"
  echo "    - /path/to/config.yaml:/config.yaml"
  echo "Exiting..." && exit 1
fi

echo "Configuration file found at $script_dir/config.yaml"

# Set up interval from environment variable
INTERVAL=${INTERVAL:-60}

# Validate interval
if [ $INTERVAL -lt 30 ] || [ $INTERVAL -gt 3600 ]; then
    echo "ERROR: Invalid interval value: $INTERVAL. Interval must be between 30 and 3600 seconds."
    echo "Exiting..." && exit 1
fi

echo "Container started successfully."

/usr/local/bin/python -u -m cfddns -i $INTERVAL /app/config.yaml
