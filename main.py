"""
Trading Automation Engine - Main Entry Point
Orchestrates all components and handles graceful shutdown
"""
import asyncio
import signal
import sys
from datetime import datetime, time
from typing import List

from config import config
from market_sim import MarketDataSimulator
from strategy_engine import StrategyEngine
from models import Strategy, EngineStats
from logger import setup_logger

logger = setup_logger(__name__)

class TradingEngine:
    """Main orchestrator for the trading automation engine"""
    
    def __init__(self):
        self.market_simulator = MarketDataSimulator()
        self.strategy_engine = StrategyEngine(self.market_simulator)
        self.shutdown_event = asyncio.Event()
        self.stats = EngineStats()
        
    async def start(self):
        """Start the trading engine"""
        logger.info("=" * 60)
        logger.info("TRADING AUTOMATION ENGINE STARTING")
        logger.info(f"Market Hours: {config.MARKET_OPEN} - {config.MARKET_CLOSE}")
        logger.info("=" * 60)
        
        # Load strategies
        strategies = self._load_strategies()
        logger.info(f"Loaded {len(strategies)} strategies")
        
        # Setup graceful shutdown
        self._setup_signal_handlers()
        
        # Start components
        tasks = [
            asyncio.create_task(self.market_simulator.start(), name="market_sim"),
            asyncio.create_task(self.strategy_engine.run(strategies), name="strategy_engine"),
            asyncio.create_task(self._monitor_market_close(), name="market_close"),
            asyncio.create_task(self._health_monitor(), name="health"),
        ]
        
        # Wait for shutdown signal
        await self.shutdown_event.wait()
        
        # Graceful shutdown
        logger.info("Initiating graceful shutdown...")
        await self._shutdown(tasks)
        
    def _load_strategies(self) -> List[Strategy]:
        """Load strategies from configuration"""
        import json
        
        try:
            with open(config.STRATEGIES_FILE, 'r') as f:
                data = json.load(f)
                strategies = [Strategy(**s) for s in data.get('strategies', [])]
                return strategies
        except FileNotFoundError:
            logger.error(f"Strategies file not found: {config.STRATEGIES_FILE}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading strategies: {e}")
            sys.exit(1)
    
    async def _monitor_market_close(self):
        """Monitor market close time and trigger shutdown"""
        try:
            while not self.shutdown_event.is_set():
                now = datetime.now().time()
                
                # Parse market close time
                close_time = datetime.strptime(config.MARKET_CLOSE, "%H:%M").time()
                
                if now >= close_time:
                    logger.info(f"Market close time reached: {config.MARKET_CLOSE}")
                    self.shutdown_event.set()
                    break
                
                await asyncio.sleep(10)  # Check every 10 seconds
        except Exception as e:
            logger.error(f"Error in market close monitor: {e}")
    
    async def _health_monitor(self):
        """Monitor and log system health"""
        try:
            while not self.shutdown_event.is_set():
                await asyncio.sleep(5)
                
                health_info = {
                    "status": "healthy",
                    "active_strategies": len(self.strategy_engine.active_strategies),
                    "total_strategies": len(self.strategy_engine.strategies),
                    "market_feed_active": self.market_simulator.is_running,
                    "current_prices": self.market_simulator.current_prices,
                }
                
                logger.info(f"[HEALTH] {health_info}")
        except Exception as e:
            logger.error(f"Error in health monitor: {e}")
    
    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown on SIGTERM/SIGINT"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def _shutdown(self, tasks):
        """Perform graceful shutdown"""
        logger.info("Closing all open positions...")
        
        # Stop market simulator
        await self.market_simulator.stop()
        
        # Force close all open strategies
        await self.strategy_engine.force_close_all()
        
        # Cancel all tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Print final summary
        self._print_summary()
    
    def _print_summary(self):
        """Print final execution summary"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 60)
        
        stats = self.strategy_engine.get_statistics()
        
        logger.info(f"Total Strategies:        {stats['total']}")
        logger.info(f"Successfully Completed:  {stats['completed']}")
        logger.info(f"Force Closed:            {stats['force_closed']}")
        logger.info(f"Failed:                  {stats['failed']}")
        logger.info(f"Never Entered:           {stats['never_entered']}")
        logger.info("")
        logger.info(f"Total PnL:               {stats['total_pnl']:+.2f}")
        logger.info(f"Winning Strategies:      {stats['winners']}")
        logger.info(f"Losing Strategies:       {stats['losers']}")
        
        logger.info("=" * 60)
        logger.info("ENGINE SHUTDOWN COMPLETE")
        logger.info("=" * 60)

async def main():
    """Main entry point"""
    engine = TradingEngine()
    try:
        config.validate()
        config.display()


        await engine.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())