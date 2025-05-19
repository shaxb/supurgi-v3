"""
Logger module for Supurgi-v3 trading bot using loguru.

This module provides enhanced logging functionalities for the entire bot, including:
- Trade execution logs
- Strategy decision logs
- Error and warning logs
- Performance logs
- Automatic source file and line number tracking

The logger integrates with the config_manager to respect log levels and
destinations specified in controller.json.
"""

import os
import sys
import inspect
from typing import Optional, Dict, Any
from loguru import logger


class Logger:
    """Main logger class for Supurgi-v3 using loguru."""
    
    def __init__(self, config_manager):
        """
        Initialize the logger with loguru.
        
        Args:
            config_manager: ConfigManager instance to get logging configuration.
        """
        self.config_manager = config_manager
        
        # Get logging configuration from controller.json
        log_config = self.config_manager.controller_config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_file_path = log_config.get('file_path', 'logs/supurgi.log')
        console_output = log_config.get('console_output', True)
        max_file_size_mb = log_config.get('max_file_size_mb', 10)
        backup_count = log_config.get('backup_count', 5)
        
        # Configure loguru (first remove default handler)
        logger.remove()
        
        # Add console handler if enabled
        if console_output:
            logger.add(
                sys.stderr,
                level=log_level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> - <level>{level}</level> - <cyan>[{extra[filename]}:{extra[line]}]</cyan> - <level>{message}</level>"
            )
        
        # Add file handler if log file path is specified
        if log_file_path:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Add rotating file handler
            logger.add(
                log_file_path,
                level=log_level,
                format="{time:YYYY-MM-DD HH:mm:ss} - {level} - [{extra[filename]}:{extra[line]}] - {message}",
                rotation=f"{max_file_size_mb} MB",
                retention=backup_count,
                compression="zip"
            )
    
    def _get_caller_info(self, stack_level=2):
        """Get the caller's filename and line number."""
        frame = inspect.currentframe()
        # Move up the stack to get the caller's frame
        for _ in range(stack_level):
            if frame.f_back is not None:
                frame = frame.f_back
            else:
                break
        
        filename = os.path.basename(frame.f_code.co_filename)
        line = frame.f_lineno
        return filename, line
    
    def log_trade(self, trade, message: str) -> None:
        """
        Log trade-related information.
        
        Args:
            trade: Trade object containing trade details.
            message: Additional message to log with the trade.
        """
        filename, line = self._get_caller_info()
        trade_info = f"[TRADE] {trade.symbol} {trade.direction} {trade.size} @ {trade.executed_price} - {message}"
        logger.bind(filename=filename, line=line).info(trade_info)
    
    def log_strategy(self, strategy_name: str, symbol: str, timeframe: str, message: str) -> None:
        """
        Log strategy decisions and signals.
        
        Args:
            strategy_name: Name of the strategy.
            symbol: Symbol being traded.
            timeframe: Timeframe of the strategy.
            message: Strategy log message.
        """
        filename, line = self._get_caller_info()
        strategy_info = f"[STRATEGY] {strategy_name} {symbol} {timeframe} - {message}"
        logger.bind(filename=filename, line=line).info(strategy_info)
    
    def log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """
        Log error messages.
        
        Args:
            message: Error message.
            exception: Optional exception object.
        """
        filename, line = self._get_caller_info()
        
        if exception:
            error_message = f"{message}: {str(exception)}"
            logger.bind(filename=filename, line=line).exception(error_message)
        else:
            logger.bind(filename=filename, line=line).error(message)
    
    def log_warning(self, message: str) -> None:
        """
        Log warning messages.
        
        Args:
            message: Warning message.
        """
        filename, line = self._get_caller_info()
        logger.bind(filename=filename, line=line).warning(message)
    
    def log_info(self, message: str) -> None:
        """
        Log informational messages.
        
        Args:
            message: Info message.
        """
        filename, line = self._get_caller_info()
        logger.bind(filename=filename, line=line).info(message)
    
    def log_debug(self, message: str) -> None:
        """
        Log debug messages.
        
        Args:
            message: Debug message.
        """
        filename, line = self._get_caller_info()
        logger.bind(filename=filename, line=line).debug(message)
