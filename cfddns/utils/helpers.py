import ipaddress
import re

def is_valid_ip_address(ip_address) -> (tuple[bool, str]):
    """Validate an IPv4 or IPv6 address"""
    try:
        ip_obj = ipaddress.ip_address(ip_address)
        if ip_obj.version == 4:
            return True, 'A'
        if ip_obj.version == 6:
            return True, 'AAAA'
        return False, None
    except ValueError:
        return False, None


def validate_config(config):
    """ Validate Cloudflare authentication configuration"""
    auth = config["cloudflare"]["authentication"]
    if "api_token" not in auth and "api_key" not in auth:
        raise ValueError("Either 'api_token' or 'api_key' is required in Cloudflare authentication configuration.")
    if "api_token" in auth and "api_key" in auth and (auth["api_token"] != "" and auth["api_key"]["api_key"] != ""):
        raise ValueError("Both 'api_token' and 'api_key' are present in Cloudflare authentication configuration.")

    # Validate Cloudflare zone ID
    if "zone_id" not in config["cloudflare"] or config["cloudflare"]["zone_id"] == "":
        raise ValueError("Missing or empty 'zone_id' value in Cloudflare configuration.")

    # Validate subdomains configuration
    for subdomain in config["cloudflare"]["subdomains"]:
        if "name" not in subdomain or subdomain["name"] == "":
            raise ValueError("Missing or empty 'name' value in subdomain configuration.") 
        if re.search(r'[^a-zA-Z0-9.-]+', subdomain["name"]):
            raise ValueError(f"Found invalid characters in subdomain: {subdomain['name']}")
        if "proxied" not in subdomain or not isinstance(subdomain["proxied"], bool):
            raise ValueError("Invalid 'proxied' value in subdomain configuration.")
        if "ttl" not in subdomain or (not isinstance(subdomain["ttl"], int) and subdomain["ttl"] not in ["1", "auto"]):
            raise ValueError("Invalid 'ttl' value in subdomain configuration.")

