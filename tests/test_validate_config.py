import unittest
from cfddns.utils.helpers import validate_config

class TestValidateConfig(unittest.TestCase):

    def test_valid_config(self):
        # Define a valid configuration
        config = {
            "cloudflare": {
                "authentication": {
                    "api_key": {
                        "api_key": "my_api_key",
                        "account_email": "my_email@example.com"
                    }
                },
                "zone_id": "my_zone_id",
                "subdomains": [
                    {
                        "name": "example.com",
                        "proxied": True,
                        "ttl": "1"
                    }
                ]
            }
        }
        # Call the validate_config function and assert no exceptions are raised
        self.assertIsNone(validate_config(config))

    def test_invalid_auth_config(self):
        # Define an invalid authentication configuration
        config = {
            "cloudflare": {
                "authentication": {},
                "zone_id": "my_zone_id",
                "subdomains": [
                    {
                        "name": "example.com",
                        "proxied": True,
                        "ttl": "XYZ"
                    }
                ]
            }
        }
        # Call the validate_config function and assert the correct exception is raised
        with self.assertRaises(ValueError):
            validate_config(config)

    # Add more test cases to cover other validation scenarios

if __name__ == '__main__':
    unittest.main()
