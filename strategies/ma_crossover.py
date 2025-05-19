"""
Moving Average Crossover Strategy Module

This module implements the Moving Average Crossover strategy.
It generates buy signals when the fast MA crosses above the slow MA,
and sell signals when the fast MA crosses below the slow MA.
"""

import pandas as pd
from strategies.base_strategy import BaseStrategy

class MA_Crossover(BaseStrategy):
    """
    A moving average crossover strategy implementation.
    Uses fast and slow moving averages to identify crossover points and generate trade signals.
    """
    
    def __init__(self, symbol, timeframe, params, broker, logger):
        """
        Initialize the MA crossover strategy.
        
        Args:
            symbol: The trading symbol
            timeframe: The timeframe for analysis
            params: Strategy-specific parameters (e.g., MA periods)
            broker: An instance of BaseBroker
            logger: An instance of Logger
        """
        super().__init__(symbol, timeframe, params, broker, logger)
        self.fast_ma_period = params.get('fast_ma_period', 20)
        self.slow_ma_period = params.get('slow_ma_period', 50)
        self.logger.log_info(f"Initialized MA_Crossover for {symbol} on {timeframe} timeframe")
        self.logger.log_info(f"Parameters: Fast MA: {self.fast_ma_period}, Slow MA: {self.slow_ma_period}")
        
    def analyze(self, data):
        """
        Analyze market data and generate trade signals.
        
        Args:
            data: DataFrame with market data
            
        Returns:
            Dict with analysis results and signals
        """
        # Ensure data is not empty
        if data is None or len(data) < self.slow_ma_period:
            self.logger.log_warning(f"Insufficient data for analysis ({len(data) if data is not None else 0} bars)")
            return {'signal': 'NEUTRAL', 'analysis': {}}
            
        # Calculate moving averages
        data = data.copy()
        data['fast_ma'] = data['close'].rolling(window=self.fast_ma_period).mean()
        data['slow_ma'] = data['close'].rolling(window=self.slow_ma_period).mean()
        
        # Drop NaN values resulting from MA calculation
        data = data.dropna()
        
        # Get current and previous values
        current = data.iloc[-1]
        previous = data.iloc[-2]
        
        # Determine signal
        signal = 'NEUTRAL'
        
        # Bullish crossover (fast MA crosses above slow MA)
        if previous['fast_ma'] <= previous['slow_ma'] and current['fast_ma'] > current['slow_ma']:
            signal = 'BUY'
            self.logger.log_info(f"BUY Signal: Fast MA ({self.fast_ma_period}) crossed above Slow MA ({self.slow_ma_period})")
        
        # Bearish crossover (fast MA crosses below slow MA)
        elif previous['fast_ma'] >= previous['slow_ma'] and current['fast_ma'] < current['slow_ma']:
            signal = 'SELL'
            self.logger.log_info(f"SELL Signal: Fast MA ({self.fast_ma_period}) crossed below Slow MA ({self.slow_ma_period})")
        
        # Return analysis results
        return {
            'signal': signal,
            'analysis': {
                'fast_ma': current['fast_ma'],
                'slow_ma': current['slow_ma'],
                'close': current['close']
            }
        }
        
    def get_name(self):
        """
        Get the strategy name.
        
        Returns:
            String with the strategy name
        """
        return f"MA_Crossover_{self.fast_ma_period}_{self.slow_ma_period}"
