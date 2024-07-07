import logging
import secrets
import sys
from typing import Dict, Any, Optional
import requests

# Initialize the logger
logger = logging.getLogger(__name__)


def generate_random_id(length: int = 32) -> str:
    return secrets.token_hex(length // 2)


class CloudflareAPI:
    def __init__(self, api_url: str, config: dict):
        self.url = api_url
        self.config = config
        self.session = requests.Session()
        self.zone_id = self.config["zone_id"]
        self._set_session_headers()
        self._get_base_domain_name()

    class TokenVerificationError(Exception):
        pass

    def _set_session_headers(self):
        api_token = self.config["auth"]["api_token"]
        if api_token not in ("", "your_api_token_here"):
            self.session.headers.update({"Authorization": "Bearer " + api_token})
        else:
            self.session.headers.update(
                {
                    "X-Auth-Email": self.config["auth"]["api_key"]["email"],
                    "X-Auth-Key": self.config["auth"]["api_key"]["key"],
                }
            )

        try:
            self.token_valid = self._verify_token()
        except self.TokenVerificationError as err:
            logger.error("%s", str(err))
            sys.exit(1)

    def _get_base_domain_name(self):
        # Fetch base domain name from Cloudflare API
        try:
            response = self.session.get(f"{self.url}/zones/{self.zone_id}")
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logger.error("Failed to fetch base domain name: %s", str(err))
            sys.exit(1)

        try:
            self.base_domain_name = response.json()["result"]["name"]
        except KeyError as err:
            logger.error(
                "Invalid response format. Could not extract base domain name: %s",
                str(err),
            )
            sys.exit(1)

        return self.base_domain_name

    def _get_fqdn(self, subdomain: str) -> str:
        # Normalize the subdomain
        name = subdomain.lower().strip()

        # Handle different subdomain formats
        if name == self.base_domain_name:
            # It's the base domain
            fqdn = self.base_domain_name
        elif name.endswith(f".{self.base_domain_name}"):
            # It's a subdomain with the base domain
            fqdn = name
        elif "." in name:
            # It's a multi-level subdomain
            fqdn = f"{name}.{self.base_domain_name}"
        else:
            # It's a single-word subdomain
            fqdn = f"{name}.{self.base_domain_name}"

        return fqdn

    def _verify_token(self) -> bool:
        url = "https://api.cloudflare.com/client/v4/user/tokens/verify"
        try:
            response = self.session.get(url=url, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as err:
            raise self.TokenVerificationError(f"API token validation failed: {err}")

    def get_dns_records(self, record_type) -> Optional[Dict[str, Any]]:

        try:
            response = self.session.get(
                f"{self.url}/zones/{self.zone_id}/dns_records?per_page=100&type={record_type}"
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            logger.error("Error getting DNS record: %s", str(err))
            return None
        except KeyError as err:
            logger.error("Error parsing DNS record response: %s", str(err))
            return None
        return response.json()

    def _needs_update(self, record, proxied, ttl, ip_data) -> tuple[bool, bool, bool]:
        """Check if a DNS record needs to be updated"""
        update_content = record["content"] != ip_data["address"]
        update_proxied = record["proxied"] != proxied
        # Check if the TTL needs to be updated (only if not proxied)
        update_ttl = not record["proxied"] and record["ttl"] != ttl
        return update_content, update_proxied, update_ttl

    def update_dns_record(
        self, subdomain: str, proxied: bool, ttl: int, ip_data: dict
    ) -> bool:
        """
        Update DNS record for a given subdomain.

        Args:
            subdomain (str): The subdomain to update.
            proxied (bool): Whether the record is proxied.
            ttl (int): Time to live for the DNS record.
            ip_data (dict): IP data containing 'address' and 'type'.

        Returns:
            bool: True if the record was updated or created, False otherwise.
        """
        # Validate input
        if (
            not isinstance(ip_data, dict)
            or "address" not in ip_data
            or "type" not in ip_data
        ):
            raise ValueError("Invalid IP data format")

        # Create fully qualified domain name
        fqdn = self._get_fqdn(subdomain)

        # Retrieve existing DNS records
        dns_records = self.get_dns_records(record_type=ip_data["type"])

        if dns_records is not None:
            for record in dns_records["result"]:
                if record["name"] == fqdn:
                    # Check if any existing record should be updated
                    update_content, update_proxied, update_ttl = self._needs_update(
                        record, proxied, ttl, ip_data
                    )

                    if any([update_content, update_proxied, update_ttl]):
                        logger.info("Updating record for %s", str(record["name"]))
                        identifier = record["id"]
                        # Create payload for DNS update
                        payload = {
                            "type": ip_data["type"],
                            "name": fqdn,
                            "content": (
                                ip_data["address"]
                                if update_content
                                else record["content"]
                            ),
                            "proxied": proxied if update_proxied else record["proxied"],
                            "ttl": ttl if update_ttl else record["ttl"],
                        }
                        try:
                            response = self.session.patch(
                                f"{self.url}/zones/{self.zone_id}/dns_records/{identifier}",
                                json=payload,
                                timeout=10,
                            )
                            response.raise_for_status()
                            return True
                        except requests.exceptions.HTTPError as err:
                            logger.error(
                                "Failed to update DNS record for %s: %s", fqdn, str(err)
                            )
                            return False
                    else:
                        logger.info(
                            "DNS record %s with address %s already up-to-date.",
                            fqdn,
                            ip_data["address"],
                        )
                    return False  # Exit after processing the matching record

            # If no existing record matched, create a new DNS record
            logger.info("Creating new record for %s", fqdn)
            payload = {
                "type": ip_data["type"],
                "name": fqdn,
                "content": ip_data["address"],
                "proxied": proxied,
                "ttl": ttl,
            }
            try:
                response = self.session.post(
                    f"{self.url}/zones/{self.zone_id}/dns_records",
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()
                return True
            except requests.exceptions.HTTPError as err:
                logger.error("Failed to create DNS record for %s: %s", fqdn, str(err))
                return False
        else:
            logger.info("No existing DNS records found for type %s", ip_data["type"])
            return False
