#!/bin/sh

set -e

script_dir=$(dirname "$0")

echo "Starting container..."

# Check if the configuration file exists in the expected location
if ! [[ -f "$script_dir/config.json" ]]; then
  echo "ERROR: Config file not found. Make sure it's mounted as a volume using:"
  echo "  volumes:"
  echo "    - /path/to/config.json:/config.json"
  echo "Exiting..." && exit 1
fi

echo "Configuration file found at $script_dir/config.json"

# Set up cron schedule from environment variable
CRON_SCHEDULE=${CRON_SCHEDULE:-"*/5 * * * *"}

# Validate cron schedule
if ! echo "$CRON_SCHEDULE" | crontab -; then
    echo "ERROR: Invalid cron schedule: $CRON_SCHEDULE"
    echo "Exiting..." && exit 1
fi

# Setup cron
echo "$CRON_SCHEDULE /bin/sh /app/run.sh >> /var/log/cron.log 2>&1" > /etc/crontabs/root

echo "Cron job scheduled to run according to the following schedule:"
crontab -l

echo ""
echo "To customize the cron schedule, set the CRON_SCHEDULE environment variable when running the container."
echo "Example: docker run -e CRON_SCHEDULE=\"0 * * * *\" image"
echo ""

echo "Container started successfully."

crond && tail -f /var/log/cron.log
