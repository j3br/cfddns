import argparse
import hashlib
import ipaddress
import logging
import signal
import sys
import time
import requests
import yaml
from pathlib import Path
from typing import Dict, Optional

from cfddns.__about__ import __program_name__, __version__
from cfddns.cloudflare.api import (
    CloudflareAPI,
    InvalidAPITokenError,
    TokenVerificationError,
)

_version = __version__
_program = __program_name__

CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def terminate_signal_handler(sig, _frame) -> None:
    """Handles termination signals (SIGINT and SIGTERM)."""

    signal_names = {signal.SIGTERM: "SIGTERM", signal.SIGINT: "SIGINT"}

    signal_name = signal_names.get(sig, f"Signal {sig}")

    logger.info("%s received, shutting down", signal_name)
    sys.exit(0)


def signal_catch_setup() -> None:
    """Set up signal handlers for SIGINT and SIGTERM."""
    signal.signal(signal.SIGTERM, terminate_signal_handler)
    signal.signal(signal.SIGINT, terminate_signal_handler)


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


def validate_config(config: Dict) -> bool:
    """
    Verify the structure and content of the configuration dictionary.
    """
    # Check if 'auth' section exists and has correct structure
    if "auth" not in config or not isinstance(config["auth"], dict):
        return False
    auth_section = config["auth"]

    # Check if 'api_token' or 'api_key' exists in 'auth' section
    if "api_token" not in auth_section and "api_key" not in auth_section:
        return False

    # If 'api_key' exists, ensure it has 'key' and 'email' keys
    if "api_key" in auth_section:
        api_key = auth_section["api_key"]
        if (
            not isinstance(api_key, dict)
            or "key" not in api_key
            or "email" not in api_key
        ):
            return False

    # Check if 'zone_id' exists and is a non-empty string
    if (
        "zone_id" not in config
        or not isinstance(config["zone_id"], str)
        or not config["zone_id"].strip()
    ):
        return False

    # Check if 'subdomains' section exists and has correct structure
    if "subdomains" not in config or not isinstance(config["subdomains"], dict):
        return False
    subdomains_section = config["subdomains"]

    # Validate each subdomain entry
    for subdomain, subdomain_config in subdomains_section.items():
        if not isinstance(subdomain, str) or not subdomain.strip():
            return False
        if (
            not isinstance(subdomain_config, dict)
            or "proxied" not in subdomain_config
            or "ttl" not in subdomain_config
        ):
            return False
        if not isinstance(subdomain_config["proxied"], bool):
            return False
        if not isinstance(subdomain_config["ttl"], (str, int)):
            return False

    # All checks passed
    return True


def init_cloudflare_api_client(api_url: str, config: dict) -> Optional[CloudflareAPI]:
    """
    Initialize a Cloudflare API client
    """
    try:
        cloudflare_api = CloudflareAPI(api_url, config)
        return cloudflare_api
    except InvalidAPITokenError as e:
        logger.error("Invalid API token: %s", str(e))
        return None
    except TokenVerificationError as e:
        logger.error("Token verification failed: %s", str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return None


def load_config(path: Path) -> Optional[Dict]:
    """
    Load a configuration file in YAML format.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
        if validate_config(config):
            return config
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", path)
    except yaml.YAMLError as exc:
        logger.error("Error parsing configuration file: %s", exc)

    return None


def get_file_hash(path: Path) -> str:
    # Calculate the SHA-256 hash of the file content
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def get_own_ip() -> Optional[Dict]:
    """
    Retrieve the public IP address of the current machine from 'https://1.1.1.1/cdn-cgi/trace'.

    Returns a dictionary with the following keys:
    - 'address': The retrieved IP address.
    - 'type': The type of IP address ('IPv4' or 'IPv6').

    Raises:
    - requests.exceptions.RequestException: If there is an error during the HTTP request.
    - ValueError: If the IP address cannot be found in the response or if there is an error parsing the response.
    """
    try:
        response = requests.get("https://1.1.1.1/cdn-cgi/trace", timeout=10)
        response.raise_for_status()  # Raise an exception for bad responses
        data = response.text.splitlines()
        ip_address = next(
            (line.split("=")[1] for line in data if line.startswith("ip")), None
        )

        if ip_address:
            result = {}
            result["address"] = ip_address

            # Determine IP type (IPv4 or IPv6)
            ip_type = "A" if ipaddress.ip_address(ip_address).version == 4 else "AAAA"
            result["type"] = ip_type
            return result
        else:
            raise ValueError("IP address not found in response")

    except requests.exceptions.RequestException as exc:
        raise Exception(f"An error occurred during the request: {exc}") from exc
    except ValueError as err:
        raise ValueError(f"Error parsing response: {err}") from err


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
