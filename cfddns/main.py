import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict

from cfddns.__about__ import __program_name__, __version__
from cfddns.cloudflare.api import CloudflareAPI
from cfddns.utils import (
    get_file_hash,
    get_own_ip,
    init_cloudflare_api_client,
    load_config,
    signal_catch_setup,
)

_version = __version__
_program = __program_name__

CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Define the command-line arguments
parser = argparse.ArgumentParser(
    prog=_program, description="Cloudflare Dynamic DNS updater"
)
parser.add_argument(
    "config",
    type=str,
    help="Path to your config.yaml file",
)
parser.add_argument(
    "-i", "--interval", type=int, help="Interval between loop iterations in seconds"
)
parser.add_argument("--version", action="version", version=f"%(prog)s {_version}")


def update_dns(config: Dict, cf_api: CloudflareAPI) -> None:
    """
    Fetch current IP address and update DNS records.

    Args:
        config (Dict): Configuration dictionary.
    """
    changes_made = 0
    logger.info("Fetching current IP address...")
    ip_data = get_own_ip()
    if ip_data:
        logger.info("Successfully fetched IP address: %s", ip_data)
    else:
        logger.error("Failed to fetch IP address. Exiting...")
        sys.exit(1)

    subdomain_count = len(config["subdomains"])
    logger.info(
        "Checking %d subdomain%s...",
        subdomain_count,
        "s" if subdomain_count != 1 else "",
    )

    for subdomain, settings in config["subdomains"].items():
        proxied = settings.get("proxied")
        ttl = settings.get("ttl")
        if ttl in ("auto", 1):
            ttl = 1
        else:
            ttl = int(ttl)
            if ttl < 60 or ttl > 86400:
                logger.warning(
                    "Invalid TTL value for %s: '%s'. Defaulting to 300.", subdomain, ttl
                )
                ttl = 300

        logger.info("Subdomain: %s, Proxied: %s, TTL: %s", subdomain, proxied, ttl)

        if cf_api.update_dns_record(subdomain, proxied, ttl, ip_data):
            changes_made += 1

    if changes_made > 0:
        logger.info(
            "Done - %d DNS record%s updated or created.",
            changes_made,
            "s" if changes_made != 1 else "",
        )
    else:
        logger.info("All DNS records up-to-date. No updates necessary.")


def main() -> None:

    args = parser.parse_args()

    # Setup signal handlers
    signal_catch_setup()

    logger.info("Initializing %s %s", _program, _version)

    if args.interval:
        # Validate interval and set to provided or default value
        if args.interval < 30 or args.interval > 3600:
            logger.warning(
                "Interval %d seconds is outside recommended range (30 to 3600). Using default value of 60 seconds.",
                args.interval,
            )
            interval_seconds = 60
        else:
            interval_seconds = args.interval
    else:
        interval_seconds = None

    config_path = Path(args.config)
    config = load_config(config_path)
    if config:
        logger.info("Configuration loaded successsfully")
    else:
        logger.warning("Invalid configuration or missing required fields. Exiting...")
        sys.exit(1)

    logger.info("Initializing Cloudflare API client...")
    cloudflare_api = init_cloudflare_api_client(CLOUDFLARE_API_URL, config)
    if cloudflare_api is None:
        sys.exit(1)

    # Run the DNS update once
    update_dns(config, cloudflare_api)

    # Initial hash of config file
    initial_hash = get_file_hash(config_path)

    # If interval is set, continue running at specified intervals
    if interval_seconds:
        while True:
            logger.info("Sleeping for %d seconds...", interval_seconds)
            time.sleep(interval_seconds)

            # Check if config file has changed
            current_hash = get_file_hash(config_path)
            if current_hash != initial_hash:
                logger.info("Detected change in config file. Reloading...")
                new_config = load_config(config_path)
                if new_config:
                    config = new_config
                    cloudflare_api = init_cloudflare_api_client(
                        CLOUDFLARE_API_URL, config
                    )  # Reinitialize API client
                    if cloudflare_api is None:
                        logger.error("Cloudflare API initialization failed.")
                        sys.exit(1)
                    initial_hash = current_hash
                    logger.info("Configuration reloaded successfully")
                else:
                    logger.warning(
                        "Failed to reload configuration. Continuing with current config."
                    )

            # Update DNS
            update_dns(config, cloudflare_api)


if __name__ == "__main__":
    main()
