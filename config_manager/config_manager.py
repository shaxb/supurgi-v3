# filepath: c:\Users\shaxb\OneDrive\Ishchi stol\Supurgi-v3\config_manager\config_manager.py
"""
Config Manager Module

This module is responsible for loading and providing configuration data for all other modules.
It handles all configuration files in the data/ directory, including:
- symbol.json: Tradable instrument configs and strategy mappings
- risk.json: Risk management parameters
- accounts.json: Trading account details
- controller.json: Global bot settings
- symbol_meta.json: Symbol metadata for risk calculations
"""

import json
import os
from typing import Dict, List, Any, Optional


class ConfigManager:
    """
    Manages configuration data for the trading bot.
    Loads and provides access to all configuration files.
    """
    
    def __init__(self, config_dir):
        """
        Initialize the config manager with the configuration directory.
        
        Args:
            config_dir: Path to the directory containing config files
        """
        self.config_dir = config_dir
        self.symbols_config = {}
        self.risk_config = {}
        self.accounts_config = {}
        self.controller_config = {}
        self.symbol_meta = {}
        
        # Load all configs on initialization
        self.load_all_configs()
        
    def load_all_configs(self):
        """Load all configuration files."""
        self.load_symbols_config()
        self.load_risk_config()
        self.load_accounts_config()
        self.load_controller_config()
        self.load_symbol_meta()
        
    def _load_json_file(self, filename):
        """
        Helper method to load and parse a JSON file.
        
        Args:
            filename: Name of the file to load
            
        Returns:
            Dict containing the parsed JSON data
        """
        try:
            with open(os.path.join(self.config_dir, filename), 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {filename} not found.")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Config file {filename} contains invalid JSON.")
            return {}
        
    def load_symbols_config(self):
        """
        Load symbol configuration from symbol.json.
        
        Returns:
            Dict containing symbol configuration
        """
        self.symbols_config = self._load_json_file('symbol.json')
        return self.symbols_config
        
    def load_risk_config(self):
        """
        Load risk parameters from risk.json.
        
        Returns:
            Dict containing risk parameters
        """
        self.risk_config = self._load_json_file('risk.json')
        return self.risk_config
        
    def load_accounts_config(self):
        """
        Load account details from accounts.json.
        
        Returns:
            Dict containing account configuration
        """
        self.accounts_config = self._load_json_file('accounts.json')
        return self.accounts_config
        
    def load_controller_config(self):
        """
        Load controller settings from controller.json.
        
        Returns:
            Dict containing controller settings
        """
        self.controller_config = self._load_json_file('controller.json')
        return self.controller_config
        
    def load_symbol_meta(self):
        """
        Load symbol metadata from symbol_meta.json.
        
        Returns:
            Dict containing symbol metadata
        """
        self.symbol_meta = self._load_json_file('symbol_meta.json')
        return self.symbol_meta
        
    def get_strategy_configs_for_symbol(self, symbol):
        """
        Get strategy configurations for a specific symbol.
        
        Args:
            symbol: The trading symbol
            
        Returns:
            List of strategy configurations for the symbol
        """
        if symbol in self.symbols_config and 'strategies' in self.symbols_config[symbol]:
            return self.symbols_config[symbol]['strategies']
        return []
    
    def get_account_config(self, account_id):
        """
        Get configuration for a specific account.
        
        Args:
            account_id: ID of the account
            
        Returns:
            Dict containing account configuration or None if not found
        """
        # First try direct lookup (for backward compatibility)
        if account_id in self.accounts_config:
            return self.accounts_config.get(account_id)
        
        # If not found, search in nested structure
        for account_name, account_data in self.accounts_config.items():
            if account_data.get('id') == account_id:
                return account_data
                
        # Log error and return None if account not found
        print(f"Account config not found for ID: {account_id}")
        return None
    
    def get_symbol_meta(self, symbol):
        """
        Get metadata for a specific symbol.
        
        Args:
            symbol: The trading symbol
            
        Returns:
            Dict containing symbol metadata or None if not found
        """
        return self.symbol_meta.get(symbol)
    
    def get_execution_mode(self):
        """
        Get the current execution mode (live or backtest).
        
        Returns:
            String indicating the execution mode
        """
        return self.controller_config.get('execution', {}).get('mode', 'backtest')
    
    def get_active_account_id(self):
        """
        Get the ID of the active trading account.
        
        Returns:
            String containing the active account ID
        """
        return self.controller_config.get('execution', {}).get('account_id', '')
        
    def get(self, key, default=None):
        """
        Get a configuration value from any configuration section.
        
        Args:
            key: The configuration key to look up
            default: Default value if key is not found
            
        Returns:
            The configuration value or default
        """
        # First check in controller.json (top level)
        if key in self.controller_config:
            return self.controller_config[key]
            
        # Check if key is in any top-level configuration
        for config_dict in [self.controller_config, self.symbols_config, 
                            self.risk_config, self.accounts_config, self.symbol_meta]:
            if key in config_dict:
                return config_dict[key]
        
        # Check in sections if using dot notation (section.key)
        if '.' in key:
            section, subkey = key.split('.', 1)
            
            # Check controller config sections first
            if section in self.controller_config:
                return self.controller_config[section].get(subkey, default)
                
            # Check other config files
            for config_dict in [self.symbols_config, self.risk_config, 
                               self.accounts_config, self.symbol_meta]:
                if section in config_dict:
                    return config_dict[section].get(subkey, default)
        
        return default
