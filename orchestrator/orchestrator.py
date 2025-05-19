# filepath: c:\Users\shaxb\OneDrive\Ishchi stol\Supurgi-v3\orchestrator\orchestrator.py
"""
Orchestrator Module

This module controls the main loop and interactions between other modules.
It initializes strategies, brokers, and other components based on configuration.

The orchestrator is responsible for:
- Managing the main bot loop
- Orchestrating interactions between modules
- Handling broker swapping (live/simulated)
- Managing strategy execution across different symbols and timeframes
"""

import datetime
import importlib
import time
from typing import Dict, List, Any, Optional, Tuple, Type

from brokers.base_broker import BaseBroker
from brokers.mt5_broker import MT5Broker
from brokers.simulated_broker import SimulatedBroker
from strategies.base_strategy import BaseStrategy
from trading.trade import Trade


class Orchestrator:
    """
    The main orchestrator for the trading bot.
    Controls the main loop and interactions between modules.
    """
    
    def __init__(self, config_manager, logger):
        """
        Initialize the orchestrator with configuration and logger.
        
        Args:
            config_manager: An instance of ConfigManager
            logger: An instance of Logger
        """
        self.config_manager = config_manager
        self.logger = logger
        
        # Will be initialized later
        self.brokers = {}
        self.active_broker = None
        self.strategies = {}
        self.risk_manager = None
        self.data_feed = None
        self.visualizer = None
        self.notifier = None
        self.running = False
        
    def initialize(self):
        """Initialize all components based on configuration."""
        self.logger.log_info("Initializing orchestrator...")
        
        # Initialize data feed (needed by brokers)
        from data_feed.data_feed import DataFeed
        self.data_feed = DataFeed(self.config_manager, self.logger)
        
        # Initialize brokers
        self._initialize_brokers()
        
        # Initialize risk manager
        from risk_manager.risk_manager import RiskManager
        self.risk_manager = RiskManager(self.config_manager, self.logger)
        self.risk_manager.initialize()
        
        # Initialize visualizer
        from visualization.visualizer import Visualizer
        self.visualizer = Visualizer(self.config_manager, self.logger)
        
        # Initialize notifier
        from notifications.telegram_notifier import TelegramNotifier
        self.notifier = TelegramNotifier(self.config_manager)
        
        # Set the active broker based on configuration
        self._set_active_broker()
        
        # Initialize strategies
        self._initialize_strategies()
        
        self.logger.log_info("Orchestrator initialized successfully")
        
    def run(self):
        """Run the main trading loop."""
        if not self.active_broker:
            self.logger.log_error("No active broker. Cannot start trading loop.")
            return
        
        self.running = True
        self.logger.log_info(f"Starting main loop with broker: {type(self.active_broker).__name__}")
        
        # Main loop
        try:
            # If in backtest mode, run the backtest
            if self.config_manager.get_execution_mode() == 'backtest':
                self._run_backtest()
            else:
                # Live trading mode
                self._run_live_trading()
                
        except KeyboardInterrupt:
            self.logger.log_info("Trading loop interrupted by user.")
        except Exception as e:
            self.logger.log_error("Error in main trading loop", e)
            self.notifier.notify_error(f"Trading bot error: {str(e)}")
        finally:
            self.running = False
            
            # Disconnect from broker
            if self.active_broker:
                self.active_broker.disconnect()
                
            self.logger.log_info("Trading loop stopped")
        
    def switch_broker(self, broker_type: str):
        """
        Switch between live and simulated broker.
        
        Args:
            broker_type: Type of broker ('mt5' or 'simulated')
        """
        if broker_type not in self.brokers:
            self.logger.log_error(f"Broker type not found: {broker_type}")
            return False
            
        self.logger.log_info(f"Switching broker to: {broker_type}")
        self.active_broker = self.brokers[broker_type]
        
        # Connect to the new broker
        if not self.active_broker.connect():
            self.logger.log_error(f"Failed to connect to broker: {broker_type}")
            return False
            
        # Reinitialize strategies with the new broker
        self._initialize_strategies()
        
        self.logger.log_info(f"Switched to broker: {broker_type}")
        return True
    
    def _initialize_brokers(self):
        """Initialize broker instances."""
        # Initialize MT5 broker
        try:
            self.brokers['mt5'] = MT5Broker(self.config_manager, self.data_feed, self.logger)
            self.logger.log_info("MT5 broker initialized")
        except Exception as e:
            self.logger.log_error("Failed to initialize MT5 broker", e)
        
        # Initialize simulated broker
        try:
            self.brokers['simulated'] = SimulatedBroker(self.config_manager, self.data_feed, self.logger)
            self.logger.log_info("Simulated broker initialized")
        except Exception as e:
            self.logger.log_error("Failed to initialize simulated broker", e)
    
    def _set_active_broker(self):
        """Set the active broker based on configuration."""
        mode = self.config_manager.get_execution_mode()
        account_id = self.config_manager.get_active_account_id()
        
        if not account_id:
            self.logger.log_error("No active account ID configured")
            return
            
        account_config = self.config_manager.get_account_config(account_id)
        if not account_config:
            self.logger.log_error(f"Account config not found for ID: {account_id}")
            return
            
        broker_type = account_config.get('broker')
        if not broker_type or broker_type not in self.brokers:
            self.logger.log_error(f"Invalid broker type: {broker_type}")
            return
            
        self.active_broker = self.brokers[broker_type]
        
        # Connect to the broker
        if not self.active_broker.connect():
            self.logger.log_error(f"Failed to connect to broker: {broker_type}")
            self.active_broker = None
            return
            
        self.logger.log_info(f"Set active broker: {broker_type}")
    
    def _initialize_strategies(self):
        """Initialize strategies for all symbols based on configuration."""
        if not self.active_broker:
            self.logger.log_error("No active broker. Cannot initialize strategies.")
            return
            
        self.strategies = {}
        
        # Get all symbols with configured strategies
        symbols_config = self.config_manager.load_symbols_config()
        
        for symbol, config in symbols_config.items():
            if 'strategies' not in config or not config['strategies']:
                continue
                
            # Initialize strategies for this symbol
            symbol_strategies = []
            
            for strategy_config in config['strategies']:
                strategy_name = strategy_config.get('name')
                timeframe = strategy_config.get('timeframe')
                
                if not strategy_name or not timeframe:
                    self.logger.log_warning(f"Invalid strategy config for {symbol}: {strategy_config}")
                    continue
                    
                try:
                    # Load the strategy class dynamically
                    module = importlib.import_module(f"strategies.{strategy_name.lower()}")
                    strategy_class = getattr(module, strategy_name)
                    
                    # Create strategy instance
                    strategy = strategy_class(
                        symbol=symbol,
                        timeframe=timeframe,
                        params=strategy_config,
                        broker=self.active_broker,
                        logger=self.logger
                    )
                    
                    symbol_strategies.append(strategy)
                    self.logger.log_info(f"Initialized strategy {strategy_name} for {symbol} on {timeframe}")
                    
                except (ImportError, AttributeError) as e:
                    self.logger.log_error(f"Failed to load strategy {strategy_name}", e)
            
            if symbol_strategies:
                self.strategies[symbol] = symbol_strategies
    
    def _run_backtest(self):
        """Run the trading bot in backtest mode."""
        self.logger.log_info("Starting backtest...")
        
        # Ensure we're using the simulated broker
        if not isinstance(self.active_broker, SimulatedBroker):
            self.logger.log_error("Backtest mode requires simulated broker")
            return
        
        # Get backtest parameters
        backtest_config = self.config_manager.controller_config.get('backtest', {})
        start_date_str = backtest_config.get('start_date')
        end_date_str = backtest_config.get('end_date')
        
        if not start_date_str or not end_date_str:
            self.logger.log_error("Backtest start_date and end_date must be configured")
            return
            
        try:
            start_date = datetime.datetime.fromisoformat(start_date_str)
            end_date = datetime.datetime.fromisoformat(end_date_str)
        except ValueError as e:
            self.logger.log_error("Invalid date format for backtest", e)
            return
        
        # Get symbols and timeframes from strategies
        symbols = list(self.strategies.keys())
        timeframes = []
        
        for symbol_strategies in self.strategies.values():
            for strategy in symbol_strategies:
                if strategy.timeframe not in timeframes:
                    timeframes.append(strategy.timeframe)
        
        # If no strategies are configured, we can't run the backtest
        if not symbols or not timeframes:
            self.logger.log_error("No strategies configured for backtest")
            return
            
        self.logger.log_info(f"Running backtest from {start_date} to {end_date}")
        self.logger.log_info(f"Symbols: {symbols}")
        self.logger.log_info(f"Timeframes: {timeframes}")
        
        # Run the backtest
        results = self.active_broker.run_backtest(start_date, end_date, symbols, timeframes)
        
        # Generate visualization
        if self.visualizer:
            try:
                self.visualizer.plot_equity_curve(results.get('equity_curve', []))
                self.visualizer.plot_trade_history(results.get('trades', []))
                performance_report = self.visualizer.generate_performance_report(
                    results.get('trades', []), 
                    results.get('equity_curve', [])
                )
                
                self.logger.log_info("Backtest performance summary:")
                self.logger.log_info(f"Initial balance: {results.get('initial_balance')}")
                self.logger.log_info(f"Final balance: {results.get('final_balance')}")
                self.logger.log_info(f"Profit: {results.get('profit')}")
                self.logger.log_info(f"Total trades: {len(results.get('trades', []))}")
                
                # Log more detailed performance metrics
                metrics = self.visualizer.calculate_performance_metrics(results.get('trades', []))
                for key, value in metrics.items():
                    self.logger.log_info(f"{key}: {value}")
                    
            except Exception as e:
                self.logger.log_error("Error generating backtest visualizations", e)
        
        self.logger.log_info("Backtest completed")
    
    def _run_live_trading(self):
        """Run the trading bot in live trading mode."""
        self.logger.log_info("Starting live trading...")
        
        # Main trading loop
        while self.running:
            try:
                # Process each symbol and its strategies
                for symbol, symbol_strategies in self.strategies.items():
                    for strategy in symbol_strategies:
                        # Run strategy analysis
                        signal = strategy.analyze()
                        
                        # If a signal was generated, process it
                        if signal:
                            self.logger.log_strategy(
                                strategy_name=strategy.__class__.__name__,
                                symbol=symbol,
                                timeframe=strategy.timeframe,
                                message=f"Generated signal: {signal}"
                            )
                            
                            # Create a trade object from the signal
                            if isinstance(signal, dict):
                                try:
                                    trade = Trade(
                                        symbol=symbol,
                                        direction=signal.get('direction'),
                                        size=signal.get('size', 0.01),
                                        order_type=signal.get('order_type', Trade.TYPE_MARKET),
                                        entry_price=signal.get('entry_price'),
                                        stop_loss=signal.get('stop_loss'),
                                        take_profit=signal.get('take_profit')
                                    )
                                    
                                    # Check trade with risk manager
                                    if self.risk_manager.evaluate_trade(trade):
                                        # Execute the trade
                                        executed_trade = self.active_broker.execute_trade(trade)
                                        
                                        # Notify about trade execution
                                        self.notifier.notify_trade(executed_trade)
                                    else:
                                        self.logger.log_warning(
                                            f"Trade rejected by risk manager: {symbol} {signal.get('direction')}"
                                        )
                                except Exception as e:
                                    self.logger.log_error(f"Error processing signal for {symbol}", e)
                
                # Small delay to prevent excessive CPU usage
                time.sleep(1)
                
            except Exception as e:
                self.logger.log_error("Error in trading loop", e)
                self.notifier.notify_error(f"Trading error: {str(e)}")
                time.sleep(5)  # Longer delay after an error
