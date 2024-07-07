import unittest
from pathlib import Path
from cfddns.main import validate_config, load_config


class TestValidateConfig(unittest.TestCase):

    def setUp(self):
        # Set up paths relative to the current script's directory
        self.test_dir = Path(__file__).resolve().parent
        self.valid_config_path = self.test_dir / "valid.yaml"
        self.invalid_config_path = self.test_dir / "invalid.yaml"

    def test_load_valid_config(self):
        # Validate the loaded configuration
        self.assertIsNotNone(load_config(self.valid_config_path))

    def test_load_invalid_config(self):
        # Assert that the configuration is None
        self.assertIsNone(load_config(self.invalid_config_path))


if __name__ == "__main__":
    unittest.main()
