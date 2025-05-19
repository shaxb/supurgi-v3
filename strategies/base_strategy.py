"""
Base Strategy Module

This module defines the abstract base class for all trading strategies.
All strategies must implement this interface to work with the bot.
"""

from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    All strategies must implement this interface to work with the bot.
    """
    
    def __init__(self, symbol, timeframe, params, broker, logger):
        """
        Initialize the strategy with symbol, timeframe, parameters, broker, and logger.
        
        Args:
            symbol: The trading symbol
            timeframe: The timeframe for analysis
            params: Strategy-specific parameters
            broker: An instance of BaseBroker
            logger: An instance of Logger
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.params = params
        self.broker = broker
        self.logger = logger
        
    @abstractmethod
    def analyze(self):
        """
        Analyze market data and generate a trade signal.
        
        Returns:
            A Trade object if a signal is generated, None otherwise
        """
        pass
        
    def get_historical_data(self, bars_count):
        """
        Get historical data for analysis.
        
        Args:
            bars_count: Number of bars to fetch
            
        Returns:
            Historical market data
        """
        return self.broker.get_historical_data(self.symbol, self.timeframe, bars_count)
        
    def get_current_price(self):
        """
        Get the current price.
        
        Returns:
            Current bid and ask prices
        """
        return self.broker.get_current_price(self.symbol)
