"""
Configuration management using environment variables
No hardcoded values - all configurable via env vars
"""
import os
from typing import List

class Config:
    """Configuration loader"""
    
    # Market timing
    MARKET_OPEN: str = os.getenv("MARKET_OPEN", "09:15")
    MARKET_CLOSE: str = os.getenv("MARKET_CLOSE", "15:20")

    # Market data simulation
    TICK_INTERVAL: float = float(os.getenv("TICK_INTERVAL", "1.0"))  # seconds
    PRICE_VOLATILITY: float = float(os.getenv("PRICE_VOLATILITY", "0.002"))  # 0.2% default
    
    # Strategy configuration
    STRATEGIES_FILE: str = os.getenv("STRATEGIES_FILE", "strategies.json")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "[%(asctime)s][%(levelname)s][%(name)s] %(message)s"
    )
    LOG_DATE_FORMAT: str = "%H:%M:%S"
    
    # Instrument settings (for market simulation)
    DEFAULT_INSTRUMENTS: List[str] = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
    BASE_PRICES = {
        "NIFTY": 20100,
        "BANKNIFTY": 45000,
        "FINNIFTY": 19500,
    }
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        
        if cls.TICK_INTERVAL <= 0:
            errors.append("TICK_INTERVAL must be positive")
        
        if not os.path.exists(cls.STRATEGIES_FILE):
            errors.append(f"Strategies file not found: {cls.STRATEGIES_FILE}")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    @classmethod
    def display(cls):
        """Display current configuration"""
        print("\n" + "=" * 60)
        print("CONFIGURATION")
        print("=" * 60)
        print(f"Market Hours:      {cls.MARKET_OPEN} - {cls.MARKET_CLOSE}")
        print(f"Tick Interval:     {cls.TICK_INTERVAL}s")
        print(f"Price Volatility:  {cls.PRICE_VOLATILITY * 100}%")
        print(f"Strategies File:   {cls.STRATEGIES_FILE}")
        print(f"Log Level:         {cls.LOG_LEVEL}")
        print("=" * 60 + "\n")

# Global config instance
config = Config()