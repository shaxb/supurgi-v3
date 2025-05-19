"""
Data Feed Module

This module is responsible for fetching and caching market data from MetaTrader 5.
It ensures data consistency and optimizes broker requests by only fetching what's needed.
"""

import os
import pandas as pd
import numpy as np
import datetime
from typing import Dict, Any, Union, Optional, List
import pathlib
import MetaTrader5 as mt5

class DataFeed:
    """
    Fetches and caches market data from MetaTrader 5.
    """
    def __init__(self, config_manager, logger):
        """
        Initialize the data feed with configuration and logger.
        
        Args:
            config_manager: An instance of ConfigManager
            logger: An instance of Logger
        """
        self.config_manager = config_manager
        self.logger = logger
        self.cache_dir = pathlib.Path(self.config_manager.get('cache_directory', 'data/market_data'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize MT5 connection
        self._initialize_mt5()
        
        # Mapping of string timeframe to MT5 timeframe constants
        self.timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
            'W1': mt5.TIMEFRAME_W1,
            'MN1': mt5.TIMEFRAME_MN1
        }
        
    def _initialize_mt5(self):
        """Initialize connection to MetaTrader 5 terminal."""
        if not mt5.initialize():
            self.logger.log_error(f"MetaTrader5 initialization failed: {mt5.last_error()}")
            return False
        
        self.logger.log_info("MetaTrader5 initialized successfully")
        return True
        
    def fetch_historical_data(self, symbol: str, timeframe: str, 
                              bars_count: Optional[int] = None,
                              start_date: Optional[datetime.datetime] = None, 
                              end_date: Optional[datetime.datetime] = None) -> pd.DataFrame:
        """
        Fetch historical data for a symbol and timeframe.
        
        Args:
            symbol: The trading symbol (e.g., 'EURUSDm')
            timeframe: The timeframe (e.g., 'M15', 'H1')
            bars_count: Number of bars to fetch (optional if date range is provided)
            start_date: Start date for historical data (optional)
            end_date: End date for historical data (optional)
            
        Returns:
            Historical market data as a DataFrame
        """
        self.logger.log_info(f"Requested data for {symbol} ({timeframe})")
        
        # Set end date to now if not provided
        if end_date is None:
            end_date = datetime.datetime.now()
        
        # Calculate start date if not provided but bars_count is
        if start_date is None and bars_count is not None:
            timeframe_seconds = self._timeframe_to_seconds(timeframe)
            start_date = end_date - datetime.timedelta(seconds=timeframe_seconds * bars_count)
        elif start_date is None and bars_count is None:
            # Default to 1000 bars if neither start date nor bars count provided
            bars_count = 1000
            timeframe_seconds = self._timeframe_to_seconds(timeframe)
            start_date = end_date - datetime.timedelta(seconds=timeframe_seconds * bars_count)
        
        # Check cache first
        cached_data = self._get_cached_data(symbol, timeframe)
        
        # Case 1: No cached data - fetch all from MT5
        if cached_data is None or cached_data.empty:
            self.logger.log_info(f"No cache found for {symbol} ({timeframe}), fetching from MT5")
            data = self._fetch_mt5_data(symbol, timeframe, start_date=start_date, end_date=end_date)
            
            if data is not None and not data.empty:
                self._save_to_cache(data, symbol, timeframe)
                return data
            else:
                self.logger.log_error(f"Failed to fetch data from MT5 for {symbol} ({timeframe})")
                return pd.DataFrame()
        
        # Case 2: Have cached data but need to check if it's up to date
        latest_cached_time = cached_data.index.max()
        
        # If we need data beyond what's in the cache
        if end_date > latest_cached_time:
            self.logger.log_info(f"Cached data is behind (latest: {latest_cached_time}, needed: {end_date})")
            
            # Fetch only the missing data from latest cache to requested end date
            new_start_date = latest_cached_time - datetime.timedelta(minutes=10)  # Overlap for continuity
            missing_data = self._fetch_mt5_data(symbol, timeframe, 
                                             start_date=new_start_date, 
                                             end_date=end_date)
            
            if missing_data is not None and not missing_data.empty:
                # Remove duplicates by index and combine with cache
                missing_data = missing_data[~missing_data.index.isin(cached_data.index)]
                updated_data = pd.concat([cached_data, missing_data]).sort_index()
                
                # Save updated data to cache
                self._save_to_cache(updated_data, symbol, timeframe)
                
                # Return the slice of data requested
                result = updated_data[(updated_data.index >= start_date) & 
                                     (updated_data.index <= end_date)]
                return result
        
        # Case 3: Cached data is sufficient, return the requested slice
        result = cached_data[(cached_data.index >= start_date) & 
                           (cached_data.index <= end_date)]
        
        return result
    
    def _fetch_mt5_data(self, symbol: str, timeframe: str,
                       start_date: Optional[datetime.datetime] = None,
                       end_date: Optional[datetime.datetime] = None,
                       bars_count: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch data directly from MT5 API.
        
        Args:
            symbol: The trading symbol
            timeframe: The timeframe string
            start_date: Start date
            end_date: End date
            bars_count: Number of bars to fetch
            
        Returns:
            Market data as DataFrame
        """
        try:
            # Convert string timeframe to MT5 timeframe constant
            mt5_timeframe = self.timeframe_map.get(timeframe)
            if mt5_timeframe is None:
                self.logger.log_error(f"Invalid timeframe: {timeframe}")
                return pd.DataFrame()
            
            # Fetch data from MT5
            if bars_count:
                # Fetch by count
                rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars_count)
            elif start_date and end_date:
                # Fetch by date range
                rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
            else:
                self.logger.log_error("Either bars_count or start_date and end_date must be provided")
                return pd.DataFrame()
            
            # Check if data was retrieved
            if rates is None or len(rates) == 0:
                self.logger.log_warning(f"No data returned from MT5 for {symbol} ({timeframe})")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            
            # Convert time column to datetime and set as index
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # Rename columns to standard format if needed
            column_map = {
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume',
                'spread': 'spread',
                'real_volume': 'real_volume'
            }
            
            # Only rename columns that exist in both the DataFrame and the map
            rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
            df.rename(columns=rename_dict, inplace=True)
            
            # Ensure data consistency
            df = self._ensure_data_consistency(df)
            
            self.logger.log_info(f"Successfully fetched {len(df)} bars from MT5 for {symbol} ({timeframe})")
            return df
            
        except Exception as e:
            self.logger.log_error(f"Error fetching data from MT5: {e}")
            return pd.DataFrame()
    
    def _get_cached_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Get data from the local cache.
        
        Args:
            symbol: The trading symbol
            timeframe: The timeframe
            
        Returns:
            Cached market data if available, otherwise None
        """
        cache_path = self.cache_dir / f"{symbol}_{timeframe}.csv"
        
        if not cache_path.exists():
            return None
        
        try:
            data = pd.read_csv(cache_path, parse_dates=['timestamp'])
            data.set_index('timestamp', inplace=True)
            return data
        except Exception as e:
            self.logger.log_warning(f"Failed to read cache: {e}")
            return None
    
    def _save_to_cache(self, data: pd.DataFrame, symbol: str, timeframe: str) -> bool:
        """
        Save data to the local cache.
        
        Args:
            data: Market data to cache
            symbol: The trading symbol
            timeframe: The timeframe
            
        Returns:
            Success status
        """
        try:
            cache_path = self.cache_dir / f"{symbol}_{timeframe}.csv"
            
            # Reset index to include timestamp as column
            data_to_save = data.copy()
            data_to_save.reset_index(inplace=True)
            data_to_save.rename(columns={'time': 'timestamp'}, inplace=True)
            
            data_to_save.to_csv(cache_path, index=False)
            self.logger.log_info(f"Saved {len(data)} bars to cache for {symbol} ({timeframe})")
            return True
        except Exception as e:
            self.logger.log_error(f"Failed to save to cache: {e}")
            return False
    
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """
        Convert a timeframe string to seconds.
        
        Args:
            timeframe: Timeframe string (e.g., 'M1', 'M5', 'H1', 'D1')
            
        Returns:
            Number of seconds in the timeframe
        """
        if timeframe.startswith('M'):  # Minutes
            return int(timeframe[1:]) * 60
        elif timeframe.startswith('H'):  # Hours
            return int(timeframe[1:]) * 3600
        elif timeframe.startswith('D'):  # Days
            return int(timeframe[1:]) * 86400
        elif timeframe.startswith('W'):  # Weeks
            return int(timeframe[1:]) * 604800
        else:
            self.logger.log_warning(f"Unknown timeframe format: {timeframe}, defaulting to 1 hour")
            return 3600
    
    def _ensure_data_consistency(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure data consistency and correct formatting.
        
        Args:
            data: Market data
            
        Returns:
            Cleaned and consistent market data
        """
        if data.empty:
            return data
            
        # Make a copy to avoid modifying the original
        clean_data = data.copy()
        
        # Ensure high is always >= open and close
        if all(col in clean_data.columns for col in ['high', 'open', 'close']):
            clean_data['high'] = clean_data[['high', 'open', 'close']].max(axis=1)
        
        # Ensure low is always <= open and close
        if all(col in clean_data.columns for col in ['low', 'open', 'close']):
            clean_data['low'] = clean_data[['low', 'open', 'close']].min(axis=1)
            
        return clean_data