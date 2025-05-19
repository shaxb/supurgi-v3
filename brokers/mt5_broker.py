"""
MetaTrader 5 Broker Module

This module implements the BaseBroker interface for MetaTrader 5.
It handles live trade execution and market data fetching from MT5.
"""

import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import MetaTrader5 as mt5

from brokers.base_broker import BaseBroker
from trading.trade import Trade, TradeStatus, TradeDirection, OrderType, CloseReason

class MT5Broker(BaseBroker):
    """
    MetaTrader 5 broker implementation.
    Handles live trade execution and market data fetching from MT5.
    """
    def __init__(self, config_manager, data_feed, logger):
        """
        Initialize the MT5 broker with configuration, data feed, and logger.
        
        Args:
            config_manager: An instance of ConfigManager
            data_feed: An instance of DataFeed
            logger: An instance of Logger
        """
        super().__init__(config_manager, data_feed, logger)
        self.mt5_account_info = {}
        self.is_connected = False
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
        
    def connect(self) -> bool:
        """
        Connect to the MetaTrader 5 terminal.
        
        Returns:
            Boolean indicating if connection was successful
        """
        if self.is_connected:
            self.logger.log_info("Already connected to MetaTrader 5")
            return True
            
        self.logger.log_info("Connecting to MetaTrader 5...")
        
        # Get connection details from config
        account_id = self.config_manager.get_active_account_id()
        account_config = self.config_manager.get_account_config(account_id)
        
        login = account_config.get('login', 0)
        password = account_config.get('password', '')
        server = account_config.get('server', '')
        
        # Initialize MT5 - using default installation path
        if not mt5.initialize():
            error = mt5.last_error()
            self.logger.log_error(f"MT5 initialization failed. Error code: {error}")
            return False
            
        # Login to MT5 account
        if login > 0:
            if not mt5.login(login=login, password=password, server=server):
                error = mt5.last_error()
                self.logger.log_error(f"MT5 login failed. Error code: {error}")
                mt5.shutdown()
                return False
                
        # Get account info
        account_info = mt5.account_info()
        if account_info is None:
            self.logger.log_error("Failed to get MT5 account info")
            mt5.shutdown()
            return False
            
        self.mt5_account_info = account_info._asdict()
        self.is_connected = True
        self.logger.log_info(f"Connected to MT5: Account #{self.mt5_account_info['login']} ({self.mt5_account_info['server']})")
        
        return True
        
    def disconnect(self) -> None:
        """Disconnect from the MetaTrader 5 terminal."""
        if self.is_connected:
            self.logger.log_info("Disconnecting from MetaTrader 5...")
            mt5.shutdown()
            self.is_connected = False
            self.mt5_account_info = {}
            self.logger.log_info("Disconnected from MetaTrader 5")
            
    def execute_trade(self, trade: Trade) -> Trade:
        """
        Execute a trade on MetaTrader 5.
        
        Args:
            trade: A Trade object representing the trade to execute
            
        Returns:
            Updated Trade object with execution details
        """
        if not self.is_connected:
            if not self.connect():
                trade.update_status(TradeStatus.REJECTED, rejection_reason="Not connected to MetaTrader 5")
                return trade
                
        self.logger.log_info(f"Executing trade: {trade}")
        
        # Validate size
        if trade.size is None or trade.size <= 0:
            trade.update_status(TradeStatus.REJECTED, rejection_reason="Invalid trade size")
            return trade
        
        # Prepare the request
        request = {
            "symbol": trade.symbol,
            "volume": float(trade.size),
            "type_time": mt5.ORDER_TIME_GTC,
            "comment": f"Supurgi-v3 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }
        
        # Handle different order types
        if trade.order_type == OrderType.MARKET:
            # Market order - get current price
            request["action"] = mt5.TRADE_ACTION_DEAL
            
            tick = mt5.symbol_info_tick(trade.symbol)
            if not tick:
                trade.update_status(TradeStatus.REJECTED, rejection_reason="Failed to get market price")
                return trade
                
            # Set price and order type based on direction
            if trade.direction == TradeDirection.BUY:
                request["type"] = mt5.ORDER_TYPE_BUY
                request["price"] = tick.ask
            else:
                request["type"] = mt5.ORDER_TYPE_SELL
                request["price"] = tick.bid
            
        elif trade.order_type == OrderType.LIMIT:
            if trade.entry_price is None:
                trade.update_status(TradeStatus.REJECTED, rejection_reason="Entry price required for limit order")
                return trade
                
            request["action"] = mt5.TRADE_ACTION_PENDING
            request["price"] = trade.entry_price
            
            if trade.direction == TradeDirection.BUY:
                request["type"] = mt5.ORDER_TYPE_BUY_LIMIT
            else:
                request["type"] = mt5.ORDER_TYPE_SELL_LIMIT
                
        elif trade.order_type == OrderType.STOP:
            if trade.entry_price is None:
                trade.update_status(TradeStatus.REJECTED, rejection_reason="Entry price required for stop order")
                return trade
                
            request["action"] = mt5.TRADE_ACTION_PENDING
            request["price"] = trade.entry_price
            
            if trade.direction == TradeDirection.BUY:
                request["type"] = mt5.ORDER_TYPE_BUY_STOP
            else:
                request["type"] = mt5.ORDER_TYPE_SELL_STOP
        
        # Add stop loss and take profit if provided
        if trade.stop_loss is not None:
            request["sl"] = trade.stop_loss
            
        if trade.take_profit is not None:
            request["tp"] = trade.take_profit
        
        # Execute the trade
        self.logger.log_info(f"Sending order to MT5: {request}")
        result = mt5.order_send(request)
        
        if result is None:
            trade.update_status(TradeStatus.REJECTED, rejection_reason="MT5 execution failed: No response")
            self.logger.log_error("MT5 trade execution failed: No response from server")
            return trade
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_desc = f"Error code: {result.retcode}, Description: {result.comment}"
            trade.update_status(TradeStatus.REJECTED, rejection_reason=f"MT5 execution failed: {error_desc}")
            self.logger.log_error(f"MT5 trade execution failed: {error_desc}")
            return trade
        
        # Update trade with execution details
        trade.id = str(result.order)
        trade.executed_price = result.price
        
        # Update trade status based on order type
        if trade.order_type == OrderType.MARKET:
            trade.update_status(TradeStatus.OPEN, 
                                executed_price=result.price, 
                                open_time=datetime.datetime.now())
            self.logger.log_info(f"Market order executed successfully: {trade}")
        else:
            # For pending orders, status remains PENDING
            self.logger.log_info(f"Pending order placed successfully: {trade}")
            
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
                self.logger.log_error("Failed to connect to MT5 while modifying trade")
                return trade
                
        if trade.id is None:
            self.logger.log_error("Cannot modify trade: Missing trade ID")
            return trade
            
        # First check if this is an open position or pending order
        position = mt5.positions_get(ticket=int(trade.id))
        is_position = position is not None and len(position) > 0
        
        if is_position:
            # Modify an open position
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": trade.symbol,
                "position": int(trade.id)
            }
            
            # Only add parameters that need to be modified
            if trade.stop_loss is not None:
                request["sl"] = trade.stop_loss
                
            if trade.take_profit is not None:
                request["tp"] = trade.take_profit
                
        else:
            # This is a pending order
            pending_order = mt5.orders_get(ticket=int(trade.id))
            if pending_order is None or len(pending_order) == 0:
                self.logger.log_error(f"Cannot find trade with ID {trade.id}")
                return trade
                
            # Modify a pending order
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": int(trade.id),
                "symbol": trade.symbol
            }
            
            # Only add parameters that need to be modified
            if trade.entry_price is not None:
                request["price"] = trade.entry_price
                
            if trade.stop_loss is not None:
                request["sl"] = trade.stop_loss
                
            if trade.take_profit is not None:
                request["tp"] = trade.take_profit
                
        # Send the modification request
        self.logger.log_info(f"Modifying trade {trade.id} with parameters: {request}")
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_code = result.retcode if result else -1
            self.logger.log_error(f"Failed to modify trade: Error code {error_code}")
            return trade
        
        self.logger.log_info(f"Successfully modified trade {trade.id}")
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
                self.logger.log_error("Failed to connect to MT5 while closing trade")
                return trade
                
        if trade.id is None:
            self.logger.log_error("Cannot close trade: Missing trade ID")
            return trade
            
        # Check if this is an open position or pending order
        position = mt5.positions_get(ticket=int(trade.id))
        is_position = position is not None and len(position) > 0
        
        if is_position:
            # Close an open position
            position_info = position[0]
            
            # Get the ticket to close
            ticket = position_info.ticket
            
            # Get current market price for the close
            tick = mt5.symbol_info_tick(trade.symbol)
            if tick is None:
                self.logger.log_error(f"Failed to get price for {trade.symbol}")
                return trade
                
            # Prepare the close request
            close_price = tick.bid if position_info.type == mt5.POSITION_TYPE_BUY else tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": trade.symbol,
                "volume": position_info.volume,
                "type": mt5.ORDER_TYPE_SELL if position_info.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "price": close_price,
                "comment": "Close position by Supurgi-v3"
            }
            
            # Send the close request
            self.logger.log_info(f"Closing position {ticket} with parameters: {request}")
            result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error_code = result.retcode if result else -1
                self.logger.log_error(f"Failed to close position: Error code {error_code}")
                return trade
            
            # Update the trade object with close information
            profit = position_info.profit
            trade.update_status(
                TradeStatus.CLOSED,
                close_price=close_price,
                profit=profit,
                close_reason=CloseReason.MANUAL,
                close_time=datetime.datetime.now()
            )
            
            self.logger.log_info(f"Position {ticket} closed successfully with profit {profit}")
            
        else:
            # This is a pending order, cancel it
            pending_order = mt5.orders_get(ticket=int(trade.id))
            if pending_order is None or len(pending_order) == 0:
                self.logger.log_error(f"Cannot find trade with ID {trade.id}")
                return trade
                
            # Cancel the pending order
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": int(trade.id),
                "comment": "Cancel order by Supurgi-v3"
            }
            
            # Send the cancel request
            self.logger.log_info(f"Cancelling order {trade.id}")
            result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error_code = result.retcode if result else -1
                self.logger.log_error(f"Failed to cancel order: Error code {error_code}")
                return trade
            
            # Update the trade object
            trade.update_status(TradeStatus.CANCELLED)
            self.logger.log_info(f"Order {trade.id} cancelled successfully")
            
        return trade
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information from MetaTrader 5.
        
        Returns:
            Account information dictionary
        """
        if not self.is_connected:
            if not self.connect():
                self.logger.log_error("Failed to connect to MT5 while getting account info")
                return {}
                
        # Get the latest account info
        account_info = mt5.account_info()
        if not account_info:
            self.logger.log_error("Failed to get MT5 account info")
            return {}
            
        # Convert to dictionary
        self.mt5_account_info = account_info._asdict()
        
        # Return standardized format
        return {
            'balance': self.mt5_account_info.get('balance', 0.0),
            'equity': self.mt5_account_info.get('equity', 0.0),
            'margin': self.mt5_account_info.get('margin', 0.0),
            'free_margin': self.mt5_account_info.get('margin_free', 0.0),
            'currency': self.mt5_account_info.get('currency', 'USD'),
            'profit': self.mt5_account_info.get('profit', 0.0),
            'leverage': self.mt5_account_info.get('leverage', 1),
            'name': self.mt5_account_info.get('name', ''),
            'server': self.mt5_account_info.get('server', '')
        }
    
    def get_open_positions(self) -> List[Trade]:
        """
        Get all open positions from MetaTrader 5.
        
        Returns:
            List of open positions as Trade objects
        """
        if not self.is_connected:
            if not self.connect():
                self.logger.log_error("Failed to connect to MT5 while getting open positions")
                return []
                
        # Get all open positions
        mt5_positions = mt5.positions_get()
        
        if mt5_positions is None:
            error = mt5.last_error()
            self.logger.log_error(f"Failed to get MT5 positions: {error}")
            return []
            
        # Convert to Trade objects
        trades = []
        for position in mt5_positions:
            try:
                direction = TradeDirection.BUY if position.type == mt5.POSITION_TYPE_BUY else TradeDirection.SELL
                
                trade = Trade(
                    symbol=position.symbol,
                    direction=direction,
                    stop_loss=position.sl,
                    take_profit=position.tp
                )
                
                # Set trade details
                trade.id = str(position.ticket)
                trade.set_size(position.volume)
                trade.order_type = OrderType.MARKET
                trade.executed_price = position.price_open
                trade.open_time = datetime.datetime.fromtimestamp(position.time)
                
                # Set status to OPEN
                trade.update_status(
                    TradeStatus.OPEN, 
                    executed_price=position.price_open, 
                    open_time=datetime.datetime.fromtimestamp(position.time)
                )
                
                # Set the profit manually
                trade._profit = position.profit
                
                trades.append(trade)
                
            except Exception as e:
                self.logger.log_error(f"Error converting MT5 position to Trade: {e}")
                
        return trades
    
    def get_pending_orders(self) -> List[Trade]:
        """
        Get all pending orders from MetaTrader 5.
        
        Returns:
            List of pending orders as Trade objects
        """
        if not self.is_connected:
            if not self.connect():
                self.logger.log_error("Failed to connect to MT5 while getting pending orders")
                return []
                
        # Get all pending orders
        mt5_orders = mt5.orders_get()
        
        if mt5_orders is None:
            error = mt5.last_error()
            self.logger.log_error(f"Failed to get MT5 orders: {error}")
            return []
            
        # Convert to Trade objects
        trades = []
        for order in mt5_orders:
            try:
                # Determine direction and order type
                if order.type == mt5.ORDER_TYPE_BUY_LIMIT or order.type == mt5.ORDER_TYPE_BUY_STOP:
                    direction = TradeDirection.BUY
                else:
                    direction = TradeDirection.SELL
                    
                if order.type == mt5.ORDER_TYPE_BUY_LIMIT or order.type == mt5.ORDER_TYPE_SELL_LIMIT:
                    order_type = OrderType.LIMIT
                else:
                    order_type = OrderType.STOP
                
                trade = Trade(
                    symbol=order.symbol,
                    direction=direction,
                    stop_loss=order.sl,
                    take_profit=order.tp
                )
                
                # Set trade details
                trade.id = str(order.ticket)
                trade.set_size(order.volume_current)
                trade.set_entry_parameters(order_type, order.price_open)
                
                trades.append(trade)
                
            except Exception as e:
                self.logger.log_error(f"Error converting MT5 order to Trade: {e}")
                
        return trades
    
    def get_historical_data(self, symbol: str, timeframe: str, bars_count: int = 1000, 
                           start_date: Optional[datetime.datetime] = None, 
                           end_date: Optional[datetime.datetime] = None) -> pd.DataFrame:
        """
        Get historical market data using the data feed.
        
        Args:
            symbol: The trading symbol
            timeframe: The timeframe (e.g., 'M15', 'H1')
            bars_count: Number of bars to fetch
            start_date: Optional start date for data
            end_date: Optional end date for data
            
        Returns:
            Historical market data as a pandas DataFrame
        """
        # Use the data feed to fetch historical data
        return self.data_feed.fetch_historical_data(
            symbol, timeframe, bars_count, start_date, end_date
        )
    
    def get_current_price(self, symbol: str) -> Dict[str, float]:
        """
        Get the current price for a symbol from MetaTrader 5.
        
        Args:
            symbol: The trading symbol
            
        Returns:
            Dictionary with bid, ask prices and timestamp
        """
        if not self.is_connected:
            if not self.connect():
                self.logger.log_error(f"Failed to connect to MT5 while getting current price for {symbol}")
                return {}
                
        # Get current price tick
        tick = mt5.symbol_info_tick(symbol)
        
        if tick is None:
            error = mt5.last_error()
            self.logger.log_error(f"Failed to get MT5 price for {symbol}: {error}")
            return {}
            
        # Return standardized format
        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'time': datetime.datetime.fromtimestamp(tick.time),
            'volume': tick.volume,
            'spread': tick.ask - tick.bid
        }
    
    def get_symbols(self) -> List[str]:
        """
        Get list of available symbols from MT5.
        
        Returns:
            List of symbol names
        """
        if not self.is_connected:
            if not self.connect():
                self.logger.log_error("Failed to connect to MT5 while getting symbols")
                return []
                
        symbols = mt5.symbols_get()
        if symbols is None:
            error = mt5.last_error()
            self.logger.log_error(f"Failed to get MT5 symbols: {error}")
            return []
            
        return [symbol.name for symbol in symbols]