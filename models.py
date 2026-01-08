"""
Data models for the trading engine
Uses dataclasses for clean, type-safe state management
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class StrategyState(Enum):
    """Strategy lifecycle states"""
    CREATED = "CREATED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FORCE_CLOSED = "FORCE_CLOSED"
    FAILED = "FAILED"

class ExitReason(Enum):
    """Reasons for strategy exit"""
    STOP_LOSS = "STOP_LOSS"
    TARGET_HIT = "TARGET_HIT"
    EXIT_CONDITION = "EXIT_CONDITION"
    TIME_EXIT = "TIME_EXIT"
    MARKET_CLOSE = "MARKET_CLOSE"
    ERROR = "ERROR"

@dataclass
class MarketTick:
    """Market data tick"""
    instrument: str
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return f"{self.instrument} @ {self.price:.2f}"

@dataclass
class Order:
    """Simulated order"""
    strategy_id: str
    instrument: str
    side: str  # BUY or SELL
    quantity: int
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return f"{self.side} {self.quantity} {self.instrument} @ {self.price:.2f}"

@dataclass
class Strategy:
    """Trading strategy definition"""
    strategy_id: str
    instrument: str
    entry_condition: str
    exit_condition: str
    quantity: int
    max_loss: float
    max_profit: float
    
    # Runtime state
    state: StrategyState = StrategyState.CREATED
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    pnl: float = 0.0
    
    def is_open(self) -> bool:
        """Check if strategy has an open position"""
        return self.state == StrategyState.OPEN
    
    def is_closed(self) -> bool:
        """Check if strategy is closed"""
        return self.state in [StrategyState.CLOSED, StrategyState.FORCE_CLOSED]
    
    def calculate_pnl(self, current_price: float) -> float:
        """Calculate current PnL"""
        if self.entry_price is None:
            return 0.0
        return (current_price - self.entry_price) * self.quantity
    
    def enter(self, price: float):
        """Enter position"""
        self.state = StrategyState.OPEN
        self.entry_price = price
        self.entry_time = datetime.now()
    
    def exit(self, price: float, reason: ExitReason):
        """Exit position"""
        self.exit_price = price
        self.exit_time = datetime.now()
        self.exit_reason = reason
        self.pnl = self.calculate_pnl(price)
        
        if reason == ExitReason.MARKET_CLOSE:
            self.state = StrategyState.FORCE_CLOSED
        else:
            self.state = StrategyState.CLOSED
    
    def mark_failed(self):
        """Mark strategy as failed"""
        self.state = StrategyState.FAILED

@dataclass
class EngineStats:
    """Engine statistics"""
    total_strategies: int = 0
    completed_strategies: int = 0
    force_closed_strategies: int = 0
    failed_strategies: int = 0
    total_pnl: float = 0.0