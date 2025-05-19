"""
Trade Converter Module

This module provides utilities for converting Trade objects to and from
external or legacy formats required by brokers, visualizers, or APIs.
"""

import datetime
from typing import Dict, Any, Optional, List
from trading.trade import Trade
from trading.trade_enums import TradeDirection, TradeStatus, OrderType

class TradeConverter:
    """
    Converts Trade objects to and from external or legacy formats.
    """
    
    @staticmethod
    def to_dict(trade: Trade) -> Dict[str, Any]:
        """
        Convert a Trade object to a dictionary.
        
        Args:
            trade: The Trade object to convert
            
        Returns:
            Dict representation of the trade
        """
        return {
            'id': trade.id,
            'symbol': trade.symbol,
            'direction': trade.direction.value if hasattr(trade.direction, 'value') else str(trade.direction),
            'size': trade.size,
            'order_type': trade.order_type.value if hasattr(trade.order_type, 'value') else str(trade.order_type),
            'entry_price': trade.entry_price,
            'stop_loss': trade.stop_loss,
            'take_profit': trade.take_profit,
            'status': trade.status.value if hasattr(trade.status, 'value') else str(trade.status),
            'open_time': trade.open_time,
            'close_time': trade.close_time,
            'executed_price': trade.executed_price,
            'profit': trade.profit,
            'commission': trade.commission,
            'swap': trade.swap,
            'signal_strength': getattr(trade, 'signal_strength', None),
            'risk_reward_ratio': getattr(trade, 'risk_reward_ratio', None)
        }
    
    @staticmethod
    def to_json(trade: Trade) -> str:
        """
        Convert a Trade object to a JSON string.
        
        Args:
            trade: The Trade object to convert
            
        Returns:
            JSON string representation of the trade
        """
        import json
        return json.dumps(TradeConverter.to_dict(trade))
        
    @staticmethod
    def trades_to_dataframe(trades: List[Trade]):
        """
        Convert a list of Trade objects to a pandas DataFrame.
        
        Args:
            trades: List of Trade objects
            
        Returns:
            pandas DataFrame with trade data
        """
        try:
            import pandas as pd
            
            if not trades:
                return pd.DataFrame()
                
            # Convert all trades to dictionaries
            trade_dicts = [TradeConverter.to_dict(trade) for trade in trades]
            
            # Create DataFrame
            df = pd.DataFrame(trade_dicts)
            
            # Convert datetime columns
            datetime_cols = ['open_time', 'close_time']
            for col in datetime_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
                    
            return df
        except ImportError:
            raise ImportError("pandas is required for trades_to_dataframe")
    
    @staticmethod
    def from_mt5_position(mt5_position) -> Trade:
        """
        Convert a MetaTrader 5 position to a Trade object.
        
        Args:
            mt5_position: A position object from MetaTrader 5
            
        Returns:
            A Trade object
        """
        # Create a Trade object from MT5 position data
        # This is a simplified implementation and would need to be expanded
        # based on the actual MT5 position object structure
        
        try:
            # Determine direction based on MT5 position type
            direction = TradeDirection.BUY if mt5_position.type == 0 else TradeDirection.SELL
            
            # Create the trade object
            trade = Trade(
                symbol=mt5_position.symbol,
                direction=direction,
                size=mt5_position.volume,
                order_type=OrderType.MARKET,
                entry_price=mt5_position.price_open,
                stop_loss=mt5_position.sl,
                take_profit=mt5_position.tp
            )
            
            # Set additional fields
            trade.id = str(mt5_position.ticket)
            trade.status = TradeStatus.OPEN
            trade.open_time = datetime.datetime.fromtimestamp(mt5_position.time)
            trade.executed_price = mt5_position.price_open
            trade.profit = mt5_position.profit
            trade.commission = mt5_position.commission
            trade.swap = mt5_position.swap
            
            return trade
        except Exception as e:
            # In a real implementation, this would be logged
            print(f"Error converting MT5 position: {e}")
            return None
        
    @staticmethod
    def to_mt5_order(trade: Trade) -> Dict[str, Any]:
        """
        Convert a Trade object to a MetaTrader 5 order request.
        
        Args:
            trade: A Trade object
            
        Returns:
            A dictionary with MT5 order parameters
        """
        # This is a simplified implementation and would need to be expanded
        # based on the actual MT5 order request structure
        
        # Determine action type based on trade direction
        action = 0 if trade.direction == Trade.DIRECTION_BUY else 1  # 0=BUY, 1=SELL
        
        # Determine order type based on trade order type
        order_type = 0  # Market order by default
        if trade.order_type == Trade.TYPE_LIMIT:
            order_type = 2  # Limit order
        elif trade.order_type == Trade.TYPE_STOP:
            order_type = 3  # Stop order
        
        # Create the MT5 order request
        request = {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": trade.symbol,
            "volume": float(trade.size),
            "type": action,
            "price": trade.entry_price,
            "sl": trade.stop_loss,
            "tp": trade.take_profit,
            "comment": f"Supurgi-v3 {trade.id if trade.id else 'trade'}",
            "type_time": 0,  # ORDER_TIME_GTC
            "type_filling": 1,  # ORDER_FILLING_RETURN
        }
        
        return request
        
    @staticmethod
    def to_visualization_format(trades: list) -> list:
        """
        Convert a list of Trade objects to a format suitable for visualization.
        
        Args:
            trades: List of Trade objects
            
        Returns:
            List of dictionaries in a format suitable for visualization
        """
        result = []
        
        for trade in trades:
            if trade.is_closed():
                # Only include closed trades with complete information
                result.append({
                    'id': trade.id,
                    'symbol': trade.symbol,
                    'direction': trade.direction,
                    'size': trade.size,
                    'entry_price': trade.executed_price,
                    'exit_price': trade.exit_price if hasattr(trade, 'exit_price') else None,
                    'open_time': trade.open_time,
                    'close_time': trade.close_time,
                    'profit': trade.profit,
                    'stop_loss': trade.stop_loss,
                    'take_profit': trade.take_profit,
                    'commission': trade.commission,
                    'swap': trade.swap,
                    'total_pnl': (trade.profit - trade.commission - trade.swap) 
                                 if trade.profit is not None else None
                })
                
        return result
