# filepath: c:\Users\shaxb\OneDrive\Ishchi stol\Supurgi-v3\trading\trade.py
"""
Trade Module

This module defines the Trade class, which is the single source of truth
for trade/order data across all modules of the bot.
"""

import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class TradeStatus(Enum):
    """Trade status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TradeDirection(Enum):
    """Trade direction enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class CloseReason(Enum):
    """Reason for closing a trade."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    MANUAL = "manual"
    STRATEGY = "strategy"
    BROKER = "broker"


class Trade:
    """
    Represents a trade or order with all relevant fields.
    
    This is the single source of truth for trade data structure across all modules.
    All modules must use this class to represent and pass trade/order data.
    """
    
    def __init__(self, 
                 symbol: str, 
                 direction: TradeDirection,
                 signal_strength: Optional[float] = None, 
                 stop_loss: Optional[float] = None,
                 take_profit: Optional[float] = None):
        """
        Initialize a new Trade object with minimal information from a strategy.
        
        Args:
            symbol: The trading symbol (e.g., 'EURUSDm')
            direction: Trade direction (TradeDirection.BUY or TradeDirection.SELL)
            signal_strength: Strength of the signal that triggered this trade (0.0-1.0)
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        self.symbol = symbol
        self.direction = direction
        self.signal_strength = signal_strength
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
        # Default values for fields that will be set later
        self.status = TradeStatus.PENDING
        self.id = None
        self.size = None  # Set by risk manager
        self.order_type = OrderType.MARKET  # Default order type
        self.entry_price = None  # Set by risk manager for limit/stop orders
        
        # Execution details (set by broker)
        self.open_time = None
        self.close_time = None
        self.executed_price = None
        self.close_price = None
        self.close_reason = None
        
        # Financial metrics (set by broker)
        self._profit = None
        self.commission = 0.0
        self.swap = 0.0
        
    def __str__(self) -> str:
        """String representation of the trade."""
        return (f"Trade(id={self.id}, symbol={self.symbol}, direction={self.direction.value}, "
                f"size={self.size}, status={self.status.value}, entry_price={self.entry_price}, "
                f"executed_price={self.executed_price})")
    
    def set_size(self, size: float) -> None:
        """
        Set the trade size (by risk manager).
        
        Args:
            size: The position size to use
            
        Raises:
            ValueError: If size is invalid
        """
        if not isinstance(size, (int, float)) or size <= 0:
            raise ValueError(f"Size must be a positive number, got: {size}")
        self.size = size
        
    def set_entry_parameters(self, order_type: OrderType, entry_price: Optional[float] = None) -> None:
        """
        Set entry parameters for the trade (by risk manager).
        
        Args:
            order_type: The order type (MARKET, LIMIT, STOP)
            entry_price: The entry price (required for LIMIT and STOP orders)
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate order type
        self.order_type = order_type
        
        # Validate entry price for limit and stop orders
        if order_type in (OrderType.LIMIT, OrderType.STOP) and entry_price is None:
            raise ValueError(f"Entry price is required for {order_type.value} orders")
        
        self.entry_price = entry_price
    
    def update_status(self, new_status: TradeStatus, **kwargs) -> None:
        """
        Update the status of the trade with required information.
        
        Args:
            new_status: New status value (TradeStatus enum)
            **kwargs: Additional parameters required for the status change
            
        Raises:
            ValueError: If the status transition is invalid or required info is missing
        """
        # Validate status transitions
        valid_transitions = {
            TradeStatus.PENDING: [TradeStatus.OPEN, TradeStatus.CANCELLED, TradeStatus.REJECTED],
            TradeStatus.OPEN: [TradeStatus.CLOSED, TradeStatus.CANCELLED],
            TradeStatus.CLOSED: [],  # Terminal state
            TradeStatus.CANCELLED: [],  # Terminal state
            TradeStatus.REJECTED: []   # Terminal state
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(
                f"Invalid status transition from {self.status.value} to {new_status.value}"
            )
            
        # Validate required fields for this status
        if new_status == TradeStatus.OPEN:
            # Required fields for opening a trade
            if 'executed_price' not in kwargs:
                raise ValueError("executed_price is required to open a trade")
                
            self.executed_price = kwargs['executed_price']
            self.open_time = kwargs.get('open_time', datetime.datetime.now())
                
        elif new_status == TradeStatus.CLOSED:
            # Required fields for closing a trade
            if 'close_price' not in kwargs:
                raise ValueError("close_price is required to close a trade")
            if 'profit' not in kwargs:
                raise ValueError("profit is required to close a trade")
                
            self.close_price = kwargs['close_price']
            self._profit = kwargs['profit']
            self.close_time = kwargs.get('close_time', datetime.datetime.now())
            self.close_reason = kwargs.get('close_reason', CloseReason.MANUAL)
            
        elif new_status == TradeStatus.REJECTED:
            # Optional rejection reason
            self.rejection_reason = kwargs.get('rejection_reason', 'Unknown')
            
        # Apply the new status
        self.status = new_status
        
    def is_pending(self) -> bool:
        """Check if the trade is pending."""
        return self.status == TradeStatus.PENDING
    
    def is_open(self) -> bool:
        """Check if the trade is open."""
        return self.status == TradeStatus.OPEN
    
    def is_closed(self) -> bool:
        """Check if the trade is closed."""
        return self.status == TradeStatus.CLOSED
    
    def is_cancelled(self) -> bool:
        """Check if the trade is cancelled."""
        return self.status == TradeStatus.CANCELLED
    
    def is_rejected(self) -> bool:
        """Check if the trade is rejected."""
        return self.status == TradeStatus.REJECTED
        
    @property
    def profit(self) -> float:
        """
        Get the profit value. This should be set by the broker.
        
        Returns:
            Current profit or 0.0 if not set
        """
        return self._profit if self._profit is not None else 0.0
