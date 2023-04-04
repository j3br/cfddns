import argparse
import json
import os
import sys
from typing import Dict, Any, Optional
import requests
from cfddns.utils.helpers import is_valid_ip_address, validate_config
from cfddns.cloudflare.cloudflare_api import CloudflareAPI

# Define the command-line arguments
parser = argparse.ArgumentParser(prog="cfddns", description='Cloudflare Dynamic DNS updater')
parser.add_argument('--config', metavar='config_file', type=str,
                    help='the path to your config.json file')


def load_config(config_file_path: Optional[str] = None) -> Dict[str, Any]:
    if config_file_path is None:
        config_file_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_file_path, encoding="utf-8") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        print(f"Error: {config_file_path} file not found.")
        sys.exit(1)
    except json.JSONDecodeError as err:
        print(f"Error: Invalid JSON in {config_file_path} file: {str(err)}")
        sys.exit(1)
    return config


def get_ip() -> str:
    try:
        response = requests.get("https://1.1.1.1/cdn-cgi/trace", timeout=10).text.split("\n")
        response.pop()
        ip_address = dict(s.split("=") for s in response)["ip"]
    except ValueError as err:
        print(f"Error parsing response: {str(err)}")
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        print(f"An error occurred: {exc}")
        sys.exit(1)

    # Validate IP address and check type
    valid, ip_type = is_valid_ip_address(ip_address)
    if valid:
        return ip_address, ip_type

    print(
        # Limit the response length in case it is too long.
        f"Error: Invalid IP address: {ip_address[:28]}..."
    )
    sys.exit(1)


def run():

    args = parser.parse_args()

    print("🚀 Initializing Cloudflare Dynamic DNS updater...")
    config = load_config(args.config)
    validate_config(config)
    print("Successfully validated config.json")

    print("Fetching IP address...")
    ip_address, ip_type = get_ip()
    ip_data = {"address": ip_address, "type": ip_type}
    print(f"Result: {ip_data}")

    print("Initializing Cloudflare API client...")
    cloudflare = CloudflareAPI(config)

    changes_made = 0
    subdomain_count = len(config['cloudflare']['subdomains'])
    print(f"Checking {subdomain_count} subdomain{'s' if subdomain_count > 1 else ''}...")
    for subdomain in config['cloudflare']['subdomains']:
        ttl = subdomain['ttl']
        if ttl in ('auto', 1):
            ttl = 1
        else:
            ttl = int(ttl)
            if ttl < 60 or ttl > 86400:
                print(f"Invalid TTL value for {subdomain['name']}: {ttl}. Defaulting to 300.")
                ttl = 300

        if cloudflare.update_dns_record(subdomain, ttl, ip_data):
            changes_made += 1

    print(f"💫 Done! {changes_made} DNS record{'s' if changes_made != 1 else ''} updated or created.")

if __name__ == "__main__":
    run()
