import argparse
import json
import os
import sys
import time
from typing import Dict, Any, Optional
import requests
from cfddns.utils.helpers import is_valid_ip_address, validate_config
from cfddns.cloudflare.cloudflare_api import CloudflareAPI

# Define the command-line arguments
parser = argparse.ArgumentParser(prog="cfddns", description='Cloudflare Dynamic DNS updater')
parser.add_argument('--config', metavar='config_file', type=str,
                    help='the path to your config.json file')
parser.add_argument('-i', '--interval', type=int,
help='Interval between loop iterations in seconds')



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
        raise ValueError(f"Error parsing response: {str(err)}") from err
    except requests.exceptions.RequestException as exc:
        raise Exception(f"An error occurred: {exc}") from exc

    # Validate IP address and check type
    result = {}
    valid, ip_type = is_valid_ip_address(ip_address)
    if valid:
        result["address"] = ip_address
        result["type"] = ip_type
        return result

    return None

def update_dns(config, cloudflare, ip_data, interval_seconds=None):
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

    if changes_made > 0:
        print(f"💫 Done! {changes_made} DNS record{'s' if changes_made != 1 else ''} updated or created.")
    else:
        print("All DNS records up-to-date. No updates necessary.")

    if interval_seconds is not None:
        print(f"\nSleeping for {interval_seconds} seconds...")
        time.sleep(interval_seconds)

def run():

    args = parser.parse_args()

    print("🚀 Starting Cloudflare Dynamic DNS updater...")
    config = load_config(args.config)
    validate_config(config)
    print("Successfully validated config.json")

    print("Initializing Cloudflare API client...")
    cloudflare = CloudflareAPI(config)

    if args.interval is not None:
        # Validate interval and set to provided or default value
        if args.interval < 30 or args.interval > 3600:
            print("❗️ Invalid interval. Using default value of 60 seconds.")
            interval_seconds = 60
        else:
            interval_seconds = args.interval

        while True:
            try:
                print("Fetching current IP address...")
                ip_data = get_ip()
                if ip_data:
                    print(f"Current IP address: {ip_data.get('address')}")
                    update_dns(config, cloudflare, ip_data, interval_seconds)
            except KeyboardInterrupt:
                print("\nCaught keyboard interrupt. Exiting...")
                break
    else:
        # Run the DNS update only once
        print("Fetching current IP address...")
        ip_address, ip_type = get_ip()
        ip_data = {"address": ip_address, "type": ip_type}
        print(f"Current IP address: {ip_address}")
        update_dns(config, cloudflare, ip_data)

if __name__ == "__main__":
    run()
