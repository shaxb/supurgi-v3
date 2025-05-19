"""
Simulated Broker Module

This module implements the BaseBroker interface for simulated trading.
It handles simulated trade execution and historical data replay for backtesting.
"""

import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

from brokers.base_broker import BaseBroker
from trading.trade import Trade, TradeStatus, TradeDirection, OrderType, CloseReason

class SimulatedBroker(BaseBroker):
    """
    Simulated broker implementation.
    Handles simulated trade execution and historical data replay for backtesting.
    """
    
    def __init__(self, config_manager, data_feed, logger):
        """
        Initialize the simulated broker.
        
        Args:
            config_manager: An instance of ConfigManager
            data_feed: An instance of DataFeed
            logger: An instance of Logger
        """
        super().__init__(config_manager, data_feed, logger)
        self.historical_data = {}
        self.current_time = None
        self.open_positions = []
        self.pending_orders = []
        self.executed_trades = []
        self.trade_id_counter = 1
        
        # Get account configuration
        account_id = self.config_manager.get_active_account_id()
        account_config = self.config_manager.get_account_config(account_id)
        
        # Initialize account info
        initial_balance = account_config.get('initial_deposit', 10000.0)
        self.account_info = {
            'balance': initial_balance,
            'equity': initial_balance,
            'margin': 0.0,
            'free_margin': initial_balance,
            'currency': account_config.get('currency', 'USD'),
            'profit': 0.0,
            'leverage': account_config.get('leverage', 100),
            'name': 'Simulation Account',
            'server': 'Simulated'
        }
        
        self.is_connected = False
        
    def connect(self) -> bool:
        """
        Connect to the simulated broker (no actual connection needed).
        
        Returns:
            True always since this is a simulated broker
        """
        self.is_connected = True
        self.logger.log_info("Connected to simulated broker")
        return True
        
    def disconnect(self) -> None:
        """Disconnect from the simulated broker (no actual disconnection needed)."""
        self.is_connected = False
        self.logger.log_info("Disconnected from simulated broker")
        
    def execute_trade(self, trade: Trade) -> Trade:
        """
        Execute a trade in the simulation.
        
        Args:
            trade: A Trade object representing the trade to execute
            
        Returns:
            Updated Trade object with execution details
        """
        if not self.is_connected:
            if not self.connect():
                trade.update_status(TradeStatus.REJECTED, rejection_reason="Not connected to simulated broker")
                return trade
                
        # Check if simulation is running for backtesting
        if self.current_time is None and trade.order_type == OrderType.MARKET:
            trade.update_status(TradeStatus.REJECTED, rejection_reason="Cannot execute market order: simulation not running")
            self.logger.log_error("Cannot execute market order: simulation not running")
            return trade
            
        # Validate size
        if trade.size is None or trade.size <= 0:
            trade.update_status(TradeStatus.REJECTED, rejection_reason="Invalid trade size")
            return trade
            
        # Set trade ID
        trade.id = f"SIM-{self.trade_id_counter}"
        self.trade_id_counter += 1
        
        # Handle different order types
        if trade.order_type == OrderType.MARKET:
            # Get current price
            current_price = self.get_current_price(trade.symbol)
            if not current_price:
                trade.update_status(TradeStatus.REJECTED, rejection_reason=f"Failed to get price for {trade.symbol}")
                return trade
                
            # Execute at current market price
            if trade.direction == TradeDirection.BUY:
                trade.executed_price = current_price.get('ask')
            else:
                trade.executed_price = current_price.get('bid')
                
            # Set execution time
            trade.open_time = self.current_time or datetime.datetime.now()
            
            # Update trade status
            trade.update_status(TradeStatus.OPEN, 
                               executed_price=trade.executed_price, 
                               open_time=trade.open_time)
            
            # Add to open positions
            self.open_positions.append(trade)
            
            # Update account info
            self._update_account_info()
            
            self.logger.log_info(f"Market order executed: {trade}")
            
        else:
            # For pending orders (LIMIT, STOP), just store the order
            self.pending_orders.append(trade)
            self.logger.log_info(f"Pending order placed: {trade}")
            
        return trade
    
    def modify_trade(self, trade: Trade) -> Trade:
        """
        Modify an existing trade's parameters (stop loss, take profit).
        
        Args:
            trade: Trade object with updated parameters
            
        Returns:
            Updated Trade object
        """
        if not self.is_connected:
            if not self.connect():
                self.logger.log_error("Failed to connect while modifying trade")
                return trade
                
        if trade.id is None:
            self.logger.log_error("Cannot modify trade: Missing trade ID")
            return trade
            
        # Find the trade to modify
        modified = False
        
        # Check open positions
        for position in self.open_positions:
            if position.id == trade.id:
                # Update stop loss and take profit
                if trade.stop_loss is not None:
                    position.stop_loss = trade.stop_loss
                    
                if trade.take_profit is not None:
                    position.take_profit = trade.take_profit
                    
                self.logger.log_info(f"Modified position {position.id}: SL={position.stop_loss}, TP={position.take_profit}")
                modified = True
                break
                
        # Check pending orders
        if not modified:
            for order in self.pending_orders:
                if order.id == trade.id:
                    # Update entry price, stop loss, and take profit
                    if trade.entry_price is not None:
                        order.entry_price = trade.entry_price
                        
                    if trade.stop_loss is not None:
                        order.stop_loss = trade.stop_loss
                        
                    if trade.take_profit is not None:
                        order.take_profit = trade.take_profit
                        
                    self.logger.log_info(f"Modified order {order.id}: " +
                                      f"Entry={order.entry_price}, SL={order.stop_loss}, TP={order.take_profit}")
                    modified = True
                    break
                    
        if not modified:
            self.logger.log_warning(f"Trade {trade.id} not found for modification")
            
        return trade
    
    def close_trade(self, trade: Trade) -> Trade:
        """
        Close a specific trade.
        
        Args:
            trade: The Trade object to close
            
        Returns:
            Updated Trade object
        """
        if not self.is_connected:
            if not self.connect():
                self.logger.log_error("Failed to connect while closing trade")
                return trade
                
        if trade.id is None:
            self.logger.log_error("Cannot close trade: Missing trade ID")
            return trade
            
        # Find the trade to close
        closed = False
        
        # Check open positions
        for position in self.open_positions[:]:
            if position.id == trade.id:
                # Get current price for closing
                current_price = self.get_current_price(position.symbol)
                if not current_price:
                    self.logger.log_error(f"Failed to get price for {position.symbol}")
                    return trade
                    
                # Close the position with current market price
                if position.direction == TradeDirection.BUY:
                    close_price = current_price.get('bid')
                else:
                    close_price = current_price.get('ask')
                    
                # Set closing details
                position.close_price = close_price
                position.close_time = self.current_time or datetime.datetime.now()
                
                # Calculate profit
                self._calculate_position_profit(position)
                
                # Update trade status
                position.update_status(
                    TradeStatus.CLOSED,
                    close_price=close_price,
                    profit=position.profit,
                    close_reason=CloseReason.MANUAL,
                    close_time=position.close_time
                )
                
                # Remove from open positions
                self.open_positions.remove(position)
                
                # Add to executed trades
                self.executed_trades.append(position)
                
                # Update account balance
                self.account_info['balance'] += position.profit
                
                self.logger.log_info(f"Position {position.id} closed with profit: {position.profit}")
                closed = True
                break
                
        # Check pending orders
        if not closed:
            for order in self.pending_orders[:]:
                if order.id == trade.id:
                    # Cancel the pending order
                    self.pending_orders.remove(order)
                    
                    # Update trade status
                    order.update_status(TradeStatus.CANCELLED)
                    
                    self.logger.log_info(f"Order {order.id} cancelled")
                    closed = True
                    break
                    
        if not closed:
            self.logger.log_warning(f"Trade {trade.id} not found for closing")
            
        # Update account information
        self._update_account_info()
        
        return trade
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get simulated account information.
        
        Returns:
            Dictionary containing account information
        """
        if not self.is_connected:
            self.connect()
            
        return self.account_info
    
    def get_open_positions(self) -> List[Trade]:
        """
        Get all open positions in the simulation.
        
        Returns:
            List of Trade objects representing open positions
        """
        if not self.is_connected:
            self.connect()
            
        return self.open_positions
    
    def get_pending_orders(self) -> List[Trade]:
        """
        Get all pending orders in the simulation.
        
        Returns:
            List of Trade objects representing pending orders
        """
        if not self.is_connected:
            self.connect()
            
        return self.pending_orders
    
    def get_historical_data(self, symbol: str, timeframe: str, bars_count: int = 1000,
                           start_date: Optional[datetime.datetime] = None,
                           end_date: Optional[datetime.datetime] = None) -> pd.DataFrame:
        """
        Get historical market data for the simulation.
        
        Args:
            symbol: The trading symbol
            timeframe: The timeframe (e.g., 'M15', 'H1')
            bars_count: Number of bars to fetch (default: 1000)
            start_date: Optional start date for data
            end_date: Optional end date for data
            
        Returns:
            Historical market data as a pandas DataFrame
        """
        # If we're in backtest mode, return data from the preloaded historical data up to current time
        key = f"{symbol}_{timeframe}"
        if key in self.historical_data and self.current_time is not None:
            data = self.historical_data[key]
            # Return data up to the current simulation time
            mask = data.index <= self.current_time
            if mask.any():
                result = data[mask].tail(bars_count)
                return result
        
        # Otherwise, use the data feed to fetch historical data
        return self.data_feed.fetch_historical_data(
            symbol, timeframe, bars_count, start_date, end_date
        )
    
    def get_current_price(self, symbol: str) -> Dict[str, float]:
        """
        Get current market price for a symbol in the simulation.
        
        Args:
            symbol: The trading symbol
            
        Returns:
            Dictionary containing bid and ask prices
        """
        if not self.is_connected:
            self.connect()
            
        # If in backtest mode, use the most recent price from historical data
        if self.current_time is not None:
            for timeframe in ['M1', 'M5', 'M15', 'H1', 'H4', 'D1']:
                key = f"{symbol}_{timeframe}"
                if key in self.historical_data:
                    data = self.historical_data[key]
                    # Find the data point closest to or exactly at current_time
                    mask = data.index <= self.current_time
                    if mask.any():
                        last_row = data[mask].iloc[-1]
                        close_price = last_row['close']
                        
                        # Simulate spread
                        spread = self._calculate_spread(symbol, close_price)
                        
                        return {
                            'bid': close_price - spread / 2,
                            'ask': close_price + spread / 2,
                            'time': self.current_time,
                            'volume': last_row.get('volume', 0),
                            'spread': spread
                        }
        
        # For live mode or if no historical data is available
        symbol_info = self.config_manager.get_symbol_config(symbol)
        if not symbol_info:
            self.logger.log_error(f"Symbol information not found for {symbol}")
            return {}
            
        # Generate a random price around the last known price or a default value
        base_price = 1.0  # Default base price
        
        # Calculate simulated spread
        spread = self._calculate_spread(symbol, base_price)
        
        return {
            'bid': base_price - spread / 2,
            'ask': base_price + spread / 2,
            'time': datetime.datetime.now(),
            'volume': 0,
            'spread': spread
        }
    
    def get_symbols(self) -> List[str]:
        """
        Get list of available symbols.
        
        Returns:
            List of symbol names
        """
        if not self.is_connected:
            self.connect()
            
        # Return symbols from configuration
        symbols = self.config_manager.get_all_symbol_configs()
        return list(symbols.keys())
    
    def run_backtest(self, start_date: datetime.datetime, end_date: datetime.datetime,
                    symbols: List[str], timeframes: List[str]) -> Dict[str, Any]:
        """
        Run a backtest simulation.
        
        Args:
            start_date: Start date for the backtest
            end_date: End date for the backtest
            symbols: List of symbols to include in the backtest
            timeframes: List of timeframes to include in the backtest
            
        Returns:
            Dictionary containing backtest results
        """
        self.logger.log_info(f"Starting backtest from {start_date} to {end_date}")
        
        # Load historical data for all symbols and timeframes
        self._load_historical_data(symbols, timeframes, start_date, end_date)
        
        # Initialize the simulation
        self.current_time = start_date
        self.open_positions = []
        self.pending_orders = []
        self.executed_trades = []
        self.trade_id_counter = 1
        
        # Reset account info
        account_id = self.config_manager.get_active_account_id()
        account_config = self.config_manager.get_account_config(account_id)
        initial_balance = account_config.get('initial_deposit', 10000.0)
        
        self.account_info = {
            'balance': initial_balance,
            'equity': initial_balance,
            'margin': 0.0,
            'free_margin': initial_balance,
            'currency': account_config.get('currency', 'USD'),
            'profit': 0.0,
            'leverage': account_config.get('leverage', 100),
            'name': 'Simulation Account',
            'server': 'Simulated'
        }
        
        # Connect to the simulated broker
        self.connect()
        
        # Generate time series for the simulation (unique timestamps from all data)
        time_series = self._generate_time_series(start_date, end_date)
        
        # Prepare results structure
        results = {
            'initial_balance': initial_balance,
            'final_balance': initial_balance,
            'profit': 0.0,
            'trades': [],
            'equity_curve': [],
            'statistics': {}
        }
        
        # Run the simulation bar by bar
        for bar_index, time in enumerate(time_series):
            # Update current time
            self.current_time = time
            self.logger.log_info(f"Processing bar at {time} ({bar_index+1}/{len(time_series)})")
            
            # Check pending orders for possible execution
            self._check_pending_orders()
            
            # Check open positions for stop loss/take profit
            self._check_stop_loss_take_profit()
            
            # Update account information
            self._update_account_info()
            
            # Record equity curve point
            results['equity_curve'].append({
                'time': time,
                'equity': self.account_info['equity'],
                'balance': self.account_info['balance']
            })
            
        # Close any remaining positions at the end of the backtest
        for position in self.open_positions[:]:
            current_price = self.get_current_price(position.symbol)
            self._close_position(position, current_price)
        
        # Cancel any remaining pending orders
        for order in self.pending_orders[:]:
            order.update_status(TradeStatus.CANCELLED)
            self.pending_orders.remove(order)
        
        # Calculate final results
        results['final_balance'] = self.account_info['balance']
        results['profit'] = results['final_balance'] - results['initial_balance']
        results['trades'] = [self._trade_to_dict(trade) for trade in self.executed_trades]
        
        # Calculate statistics
        results['statistics'] = self._calculate_backtest_statistics()
        
        self.logger.log_info(f"Backtest completed. Final profit: {results['profit']}")
        return results
    
    def advance_time(self) -> datetime.datetime:
        """
        Advance the simulation to the next bar.
        
        Returns:
            New current time
        """
        if self.current_time is None:
            self.logger.log_error("Cannot advance time: simulation not running")
            return None
        
        # Find the next time step in the time series
        time_series = self._generate_time_series(self.current_time, 
                                               datetime.datetime.max)
        
        if len(time_series) > 1:
            # Set the new current time
            old_time = self.current_time
            self.current_time = time_series[1]  # Skip the current time
            self.logger.log_info(f"Advanced time from {old_time} to {self.current_time}")
            
            # Check pending orders for possible execution
            self._check_pending_orders()
            
            # Check open positions for stop loss/take profit
            self._check_stop_loss_take_profit()
            
            # Update account information
            self._update_account_info()
            
            return self.current_time
        else:
            self.logger.log_warning("Cannot advance time: reached end of data")
            return self.current_time
    
    def _load_historical_data(self, symbols: List[str], timeframes: List[str],
                             start_date: datetime.datetime, end_date: datetime.datetime) -> None:
        """
        Load historical data for the backtest.
        
        Args:
            symbols: List of symbols to load data for
            timeframes: List of timeframes to load data for
            start_date: Start date for historical data
            end_date: End date for historical data
        """
        self.historical_data = {}
        
        for symbol in symbols:
            for timeframe in timeframes:
                key = f"{symbol}_{timeframe}"
                self.logger.log_info(f"Loading historical data for {key}")
                
                # Load data using the data feed
                data = self.data_feed.fetch_historical_data(symbol, timeframe, None,
                                                          start_date, end_date)
                
                if isinstance(data, pd.DataFrame) and not data.empty:
                    self.historical_data[key] = data
                    self.logger.log_info(f"Loaded {len(data)} bars for {key}")
                else:
                    self.logger.log_warning(f"No historical data found for {key}")
    
    def _generate_time_series(self, start_date: datetime.datetime, 
                             end_date: datetime.datetime) -> List[datetime.datetime]:
        """
        Generate a time series for the simulation.
        
        Args:
            start_date: Start date for the time series
            end_date: End date for the time series
            
        Returns:
            List of datetime objects representing the time series
        """
        # Collect all unique timestamps from the historical data
        timestamps = set()
        
        for key, data in self.historical_data.items():
            if isinstance(data, pd.DataFrame) and not data.empty:
                mask = (data.index >= start_date) & (data.index <= end_date)
                timestamps.update(data.loc[mask].index.tolist())
        
        # Sort timestamps
        time_series = sorted(list(timestamps))
        
        return time_series
    
    def _update_account_info(self) -> None:
        """Update account information based on open positions."""
        # Calculate total unrealized profit
        total_profit = 0.0
        total_margin = 0.0
        
        for position in self.open_positions:
            # Update position profit
            self._calculate_position_profit(position)
            total_profit += position.profit
            
            # Calculate required margin
            margin = self._calculate_position_margin(position)
            total_margin += margin
        
        # Update account information
        self.account_info['profit'] = total_profit
        self.account_info['margin'] = total_margin
        self.account_info['equity'] = self.account_info['balance'] + total_profit
        self.account_info['free_margin'] = self.account_info['equity'] - total_margin
    
    def _check_pending_orders(self) -> None:
        """Check if any pending orders should be executed."""
        for order in self.pending_orders[:]:
            current_price = self.get_current_price(order.symbol)
            if not current_price:
                continue
                
            executed = False
            
            # Check if limit order should be executed
            if order.order_type == OrderType.LIMIT:
                if (order.direction == TradeDirection.BUY and 
                    current_price['ask'] <= order.entry_price):
                    executed = True
                    execution_price = order.entry_price
                elif (order.direction == TradeDirection.SELL and 
                      current_price['bid'] >= order.entry_price):
                    executed = True
                    execution_price = order.entry_price
            
            # Check if stop order should be executed
            elif order.order_type == OrderType.STOP:
                if (order.direction == TradeDirection.BUY and 
                    current_price['ask'] >= order.entry_price):
                    executed = True
                    execution_price = order.entry_price
                elif (order.direction == TradeDirection.SELL and 
                      current_price['bid'] <= order.entry_price):
                    executed = True
                    execution_price = order.entry_price
            
            # Execute the order if conditions are met
            if executed:
                # Update order status
                order.executed_price = execution_price
                order.open_time = self.current_time
                order.update_status(TradeStatus.OPEN, 
                                   executed_price=execution_price, 
                                   open_time=self.current_time)
                
                # Move from pending orders to open positions
                self.pending_orders.remove(order)
                self.open_positions.append(order)
                
                self.logger.log_info(f"Order executed: {order}")
    
    def _check_stop_loss_take_profit(self) -> None:
        """Check if any open positions hit their stop loss or take profit levels."""
        for position in self.open_positions[:]:
            current_price = self.get_current_price(position.symbol)
            if not current_price:
                continue
                
            # Update position profit
            self._calculate_position_profit(position)
            
            # Check stop loss
            if position.stop_loss is not None:
                if (position.direction == TradeDirection.BUY and 
                    current_price['bid'] <= position.stop_loss):
                    self._close_position(position, {'price': position.stop_loss}, 
                                       close_reason=CloseReason.STOP_LOSS)
                    continue
                
                if (position.direction == TradeDirection.SELL and 
                    current_price['ask'] >= position.stop_loss):
                    self._close_position(position, {'price': position.stop_loss}, 
                                       close_reason=CloseReason.STOP_LOSS)
                    continue
            
            # Check take profit
            if position.take_profit is not None:
                if (position.direction == TradeDirection.BUY and 
                    current_price['bid'] >= position.take_profit):
                    self._close_position(position, {'price': position.take_profit}, 
                                       close_reason=CloseReason.TAKE_PROFIT)
                    continue
                
                if (position.direction == TradeDirection.SELL and 
                    current_price['ask'] <= position.take_profit):
                    self._close_position(position, {'price': position.take_profit}, 
                                       close_reason=CloseReason.TAKE_PROFIT)
                    continue
    
    def _close_position(self, position: Trade, price_info: Dict[str, Any],
                       close_reason: CloseReason = CloseReason.MANUAL) -> None:
        """
        Close an open position.
        
        Args:
            position: Trade object representing the position to close
            price_info: Dictionary containing price information
            close_reason: Reason for closing the position
        """
        # Set closing details
        position.close_time = self.current_time or datetime.datetime.now()
        
        # Get the closing price
        if 'price' in price_info:
            close_price = price_info['price']
        elif position.direction == TradeDirection.BUY:
            close_price = price_info.get('bid', position.executed_price)
        else:  # SELL
            close_price = price_info.get('ask', position.executed_price)
        
        position.close_price = close_price
        
        # Calculate final profit
        self._calculate_position_profit(position, close_price)
        
        # Update position status
        position.update_status(
            TradeStatus.CLOSED,
            close_price=close_price,
            profit=position.profit,
            close_reason=close_reason,
            close_time=position.close_time
        )
        
        # Remove from open positions
        self.open_positions.remove(position)
        
        # Add to executed trades
        self.executed_trades.append(position)
        
        # Update account balance
        self.account_info['balance'] += position.profit
        
        self.logger.log_info(f"Position {position.id} closed. Reason: {close_reason.value}, Profit: {position.profit}")
    
    def _calculate_spread(self, symbol: str, price: float) -> float:
        """
        Calculate the spread for a symbol.
        
        Args:
            symbol: Trading symbol
            price: Current price
            
        Returns:
            Spread value
        """
        # Get symbol metadata for accurate spread calculation
        symbol_config = self.config_manager.get_symbol_config(symbol)
        
        if symbol_config and 'spread' in symbol_config:
            # Fixed spread in points
            return float(symbol_config['spread']) * float(symbol_config.get('pip_value', 0.0001))
        
        if symbol_config and 'pip_value' in symbol_config:
            pip_value = float(symbol_config['pip_value'])
            return pip_value * 10  # Simplified: spread is 1 pip
        
        # Fallback to a percentage-based spread (0.01%)
        return price * 0.0001
    
    def _calculate_position_profit(self, position: Trade, 
                                  close_price: Optional[float] = None) -> float:
        """
        Calculate the current profit for a position.
        
        Args:
            position: The position to calculate profit for
            close_price: Close price for calculation (optional)
            
        Returns:
            Current profit
        """
        if position.executed_price is None:
            return 0.0
        
        # Get current price if not provided
        if close_price is None:
            price_data = self.get_current_price(position.symbol)
            if not price_data:
                return 0.0
            
            # Use appropriate price (bid for buy, ask for sell)
            if position.direction == TradeDirection.BUY:
                close_price = price_data.get('bid', 0)
            else:
                close_price = price_data.get('ask', 0)
        
        # Calculate pip difference
        pip_diff = 0.0
        if position.direction == TradeDirection.BUY:
            pip_diff = close_price - position.executed_price
        else:  # SELL
            pip_diff = position.executed_price - close_price
        
        # Get symbol data for accurate profit calculation
        symbol_config = self.config_manager.get_symbol_config(position.symbol)
        pip_value = float(symbol_config.get('pip_value', 0.0001))
        contract_size = float(symbol_config.get('contract_size', 100000))
        
        # Calculate profit
        profit = pip_diff / pip_value * position.size * contract_size
        
        # Apply commission and swap (if any)
        commission = getattr(position, 'commission', 0.0)
        swap = getattr(position, 'swap', 0.0)
        profit -= commission + swap
        
        # Update position profit
        position.profit = profit
        
        return profit
    
    def _calculate_position_margin(self, position: Trade) -> float:
        """
        Calculate the required margin for a position.
        
        Args:
            position: The position to calculate margin for
            
        Returns:
            Required margin
        """
        if position.executed_price is None or position.size is None:
            return 0.0
        
        # Get symbol data
        symbol_config = self.config_manager.get_symbol_config(position.symbol)
        contract_size = float(symbol_config.get('contract_size', 100000))
        
        # Calculate position value
        position_value = position.executed_price * position.size * contract_size
        
        # Calculate required margin based on leverage
        leverage = float(self.account_info.get('leverage', 100))
        if leverage <= 0:
            leverage = 100  # Default to 100:1 if invalid
            
        margin = position_value / leverage
        
        return margin
    
    def _calculate_backtest_statistics(self) -> Dict[str, Any]:
        """
        Calculate statistics for the backtest.
        
        Returns:
            Dictionary of backtest statistics
        """
        statistics = {
            'total_trades': len(self.executed_trades),
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'average_profit': 0.0,
            'average_loss': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_percentage': 0.0
        }
        
        if not self.executed_trades:
            return statistics
        
        # Calculate basic statistics
        for trade in self.executed_trades:
            if trade.profit > 0:
                statistics['winning_trades'] += 1
                statistics['total_profit'] += trade.profit
            else:
                statistics['losing_trades'] += 1
                statistics['total_loss'] += abs(trade.profit)
        
        # Calculate derivative statistics
        if statistics['total_trades'] > 0:
            statistics['win_rate'] = statistics['winning_trades'] / statistics['total_trades']
            
        if statistics['winning_trades'] > 0:
            statistics['average_profit'] = statistics['total_profit'] / statistics['winning_trades']
            
        if statistics['losing_trades'] > 0:
            statistics['average_loss'] = statistics['total_loss'] / statistics['losing_trades']
            
        if statistics['total_loss'] > 0:
            statistics['profit_factor'] = statistics['total_profit'] / statistics['total_loss']
        
        # Calculate drawdown
        balance_peaks = []
        current_balance = self.account_info['initial_deposit']
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        
        for trade in sorted(self.executed_trades, key=lambda t: t.close_time):
            current_balance += trade.profit
            
            # Update peak balance
            if not balance_peaks or current_balance > balance_peaks[-1]:
                balance_peaks.append(current_balance)
            else:
                # Calculate drawdown
                peak = max(balance_peaks)
                drawdown = peak - current_balance
                drawdown_pct = drawdown / peak if peak > 0 else 0
                
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_pct = drawdown_pct
        
        statistics['max_drawdown'] = max_drawdown
        statistics['max_drawdown_percentage'] = max_drawdown_pct * 100  # Convert to percentage
        
        return statistics
    
    def _trade_to_dict(self, trade: Trade) -> Dict[str, Any]:
        """
        Convert a Trade object to a dictionary for serialization.
        
        Args:
            trade: Trade object to convert
            
        Returns:
            Dictionary representation of the trade
        """
        trade_dict = {
            'id': trade.id,
            'symbol': trade.symbol,
            'direction': trade.direction.value if hasattr(trade.direction, 'value') else trade.direction,
            'order_type': trade.order_type.value if hasattr(trade.order_type, 'value') else trade.order_type,
            'size': trade.size,
            'status': trade.status.value if hasattr(trade.status, 'value') else trade.status,
            'entry_price': trade.entry_price,
            'executed_price': trade.executed_price,
            'close_price': getattr(trade, 'close_price', None),
            'stop_loss': trade.stop_loss,
            'take_profit': trade.take_profit,
            'open_time': trade.open_time.isoformat() if trade.open_time else None,
            'close_time': trade.close_time.isoformat() if hasattr(trade, 'close_time') and trade.close_time else None,
            'profit': trade.profit,
            'close_reason': trade.close_reason.value if hasattr(trade, 'close_reason') and trade.close_reason else None,
            'commission': getattr(trade, 'commission', 0.0),
            'swap': getattr(trade, 'swap', 0.0)
        }
        return trade_dict