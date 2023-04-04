import sys
from typing import Dict, Any
import requests

API_URL = "https://api.cloudflare.com/client/v4"

class CloudflareAPI:
    def __init__(self, config: dict):
        self.config = config
        self.session = requests.Session()
        self.zone_id = self.config['cloudflare']['zone_id']
        self._set_session_headers()
        self._get_base_domain_name()

    class TokenVerificationError(Exception):
        pass

    def _set_session_headers(self):
        api_token = self.config['cloudflare']['authentication']['api_token']
        if api_token not in ('', 'your_api_token_here'):
            self.session.headers.update({
                "Authorization": "Bearer " + api_token
            })
        else:
            self.session.headers.update({
                "X-Auth-Email": self.config['cloudflare']['authentication']['api_key']['account_email'],
                "X-Auth-Key": self.config['cloudflare']['authentication']['api_key']['api_key'],
            })

        try:
            self.token_valid = self._verify_token()
        except self.TokenVerificationError as err:
            print(f"Error: {str(err)}")
            sys.exit(1)

    def _get_base_domain_name(self):
        # Fetch base domain name from Cloudflare API
        try:
            response = self.session.get(f"{API_URL}/zones/{self.zone_id}")
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(f"Error: Failed to fetch base domain name: {err}")
            sys.exit(1)

        try:
            self.base_domain_name = response.json()["result"]["name"]
        except KeyError as err:
            print(f"Error: Invalid response format. Could not extract base domain name: {err}")
            sys.exit(1)

        return self.base_domain_name



    def _verify_token(self) -> bool:
        url = "https://api.cloudflare.com/client/v4/user/tokens/verify"
        try:
            response = self.session.get(url=url, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as err:
            raise self.TokenVerificationError(f"API token validation failed: {err}")


    def get_dns_records(self, record_type) -> Dict[str, Any]:
        try:
            response = self.session.get(f"{API_URL}/zones/{self.zone_id}/dns_records?per_page=100&type={record_type}")
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            print(f"Error getting DNS record: {err}")
            return None
        except KeyError as err:
            print(f"Error parsing DNS record response: {err}")
            return None
        return response.json()

    def _needs_update(self, record, subdomain, ttl, ip_data):
        """Check if a DNS record needs to be updated"""
        update_content = record["content"] != ip_data["address"]
        update_proxied = record["proxied"] != subdomain["proxied"]
        update_ttl = not record["proxied"] and record["ttl"] != ttl
        return update_content, update_proxied, update_ttl


    def update_dns_record(self, subdomain: str, ttl: int, ip_data: dict):
        # Validate input
        if not isinstance(ip_data, dict) or "address" not in ip_data or "type" not in ip_data:
            raise ValueError("Invalid IP data format")

        # Create fully qualified domain name
        name = subdomain["name"].lower().strip()
        fqdn = (
            self.base_domain_name
            if name == "" or name.endswith(self.base_domain_name)
            else f"{name}.{self.base_domain_name}"
        )

        dns_records = self.get_dns_records(record_type=ip_data["type"])
        if dns_records is not None:
            for record in dns_records["result"]:
                if record["name"] == fqdn:

                    # Check if any existing record should be updated
                    update_content, update_proxied, update_ttl = self._needs_update(record, subdomain, ttl, ip_data)

                    if any([update_content, update_proxied, update_ttl]):
                        print(f"Updating record {str(record['name'])}")
                        identifier = record["id"]
                        # Create payload for DNS update
                        payload = {
                            "type": ip_data["type"],
                            "name": fqdn,
                            "content": ip_data["address"] if update_content else record["content"],
                            "proxied": subdomain["proxied"] if update_proxied else record["proxied"],
                            "ttl": ttl if update_ttl else record["ttl"]
                        }
                        try:
                            response = self.session.put(
                                f"{API_URL}/zones/{self.zone_id}/dns_records/{identifier}",
                                json=payload,
                                timeout=10
                            )
                            response.raise_for_status()
                            return True
                        except requests.exceptions.HTTPError as err:
                            print(f"Failed to update DNS record for {fqdn}: {err}")
                            return False
                    # else:
                    #     print(f"DNS record {fqdn} with address {ip_data['address']} already exists.")
                    break

            else: # Create new DNS record if no existing record found
                print(f"Creating new record {fqdn}")
                # Create payload for new DNS record
                payload = {
                    "type": ip_data["type"],
                    "name": fqdn,
                    "content": ip_data["address"],
                    "proxied": subdomain["proxied"],
                    "ttl": ttl
                }
                try:
                    response = self.session.post(
                        f"{API_URL}/zones/{self.zone_id}/dns_records",
                        json=payload,
                        timeout=10
                    )
                    response.raise_for_status()
                    return True
                except requests.exceptions.HTTPError as err:
                    print(f"Failed to create DNS record for {fqdn}: {err}")
                    return False
        else:
            print(f"No existing DNS records found for type {ip_data['type']}")
        return
