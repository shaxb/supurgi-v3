"""
Test the get method of the ConfigManager class.
"""
import unittest
import os
from config_manager.config_manager import ConfigManager

class TestConfigManagerGet(unittest.TestCase):
    """Test cases for the ConfigManager get method."""
    
    def setUp(self):
        """Set up the test environment."""
        # Use the actual data directory for tests
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.config_manager = ConfigManager(config_dir)
        self.config_manager.load_all_configs()
    
    def test_get_direct_key(self):
        """Test getting a top-level key directly from controller config."""
        self.assertEqual(
            self.config_manager.get('logging').get('level'),
            'INFO'
        )
    
    def test_get_with_dot_notation(self):
        """Test getting a nested key using dot notation."""
        self.assertEqual(
            self.config_manager.get('logging.level'),
            'INFO'
        )
        
        self.assertEqual(
            self.config_manager.get('execution.mode'),
            'backtest'
        )
        
    def test_get_with_default(self):
        """Test that default is returned when key doesn't exist."""
        self.assertEqual(
            self.config_manager.get('nonexistent_key', 'default_value'),
            'default_value'
        )
        
        self.assertEqual(
            self.config_manager.get('logging.nonexistent', 'default_value'),
            'default_value'
        )
    
    def test_get_backtest_data_directory(self):
        """Test getting the data directory from backtest config."""
        self.assertEqual(
            self.config_manager.get('backtest.data_directory'),
            'data/historical'
        )

if __name__ == '__main__':
    unittest.main()
