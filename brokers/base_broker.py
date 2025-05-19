# filepath: c:\Users\shaxb\OneDrive\Ishchi stol\Supurgi-v3\brokers\base_broker.py
"""
Base Broker Module

This module defines the abstract base class for all broker implementations.
It provides a unified interface for executing trades and fetching market data.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from trading.trade import Trade


class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations.
    Provides a unified interface for executing trades and fetching market data.
    """
    
    def __init__(self, config_manager, data_feed, logger):
        """
        Initialize the broker with configuration, data feed, and logger.
        
        Args:
            config_manager: An instance of ConfigManager
            data_feed: An instance of DataFeed
            logger: An instance of Logger
        """
        self.config_manager = config_manager
        self.data_feed = data_feed
        self.logger = logger
        self.account_info = {}
        
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
        
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the broker."""
        pass
        
    @abstractmethod
    def execute_trade(self, trade: Trade) -> Trade:
        """
        Execute a trade.
        
        Args:
            trade: Trade object containing trade details
            
        Returns:
            Updated Trade object with execution details
        """
        pass
        
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Returns:
            Dictionary containing account information
        """
        pass
        
    @abstractmethod
    def get_open_positions(self) -> List[Trade]:
        """
        Get all open positions.
        
        Returns:
            List of Trade objects representing open positions
        """
        pass
        
    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, bars_count: int) -> Any:
        """
        Get historical market data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., 'M1', 'H1', 'D1')
            bars_count: Number of bars to fetch
            
        Returns:
            Market data in the format required by strategies
        """
        pass
        
    @abstractmethod
    def get_current_price(self, symbol: str) -> Dict[str, float]:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary containing bid and ask prices
        """
        pass
