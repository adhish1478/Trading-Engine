"""
Market Data Simulator
Generates realistic price ticks for multiple instruments
Uses asyncio.Queue for non-blocking broadcast
"""
import asyncio
import random
from datetime import datetime
from typing import Dict, Set
from collections import defaultdict

from models import MarketTick
from config import config
from logger import setup_logger

logger = setup_logger(__name__)

class MarketDataSimulator:
    """Simulates live market data feed"""
    
    def __init__(self):
        self.is_running = False
        self.subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self.current_prices: Dict[str, float] = config.BASE_PRICES.copy()
        self._task = None
        
    async def start(self):
        """Start market data generation"""
        self.is_running = True
        logger.info("Market data simulator started")
        
        try:
            while self.is_running:
                await self._generate_and_broadcast_ticks()
                await asyncio.sleep(config.TICK_INTERVAL)
        except asyncio.CancelledError:
            logger.info("Market data simulator cancelled")
        except Exception as e:
            logger.error(f"Market simulator error: {e}", exc_info=True)
        finally:
            self.is_running = False
    
    async def stop(self):
        """Stop market data generation"""
        self.is_running = False
        logger.info("Market data simulator stopped")
        
        # Notify all subscribers with None to signal completion
        for instrument in self.subscribers:
            for queue in self.subscribers[instrument]:
                try:
                    await queue.put(None)
                except:
                    pass
    
    def subscribe(self, instrument: str) -> asyncio.Queue:
        """Subscribe to market data for an instrument"""
        queue = asyncio.Queue(maxsize=100)
        self.subscribers[instrument].add(queue)
        logger.debug(f"New subscription for {instrument}")
        return queue
    
    def unsubscribe(self, instrument: str, queue: asyncio.Queue):
        """Unsubscribe from market data"""
        if instrument in self.subscribers:
            self.subscribers[instrument].discard(queue)
    
    async def _generate_and_broadcast_ticks(self):
        """Generate price ticks and broadcast to subscribers"""
        for instrument in list(self.subscribers.keys()):
            # Generate new price (random walk)
            current_price = self.current_prices[instrument]
            change_percent = random.uniform(-config.PRICE_VOLATILITY, config.PRICE_VOLATILITY)
            new_price = current_price * (1 + change_percent)
            
            # Round to 2 decimals
            new_price = round(new_price, 2)
            self.current_prices[instrument] = new_price
            
            # Create tick
            tick = MarketTick(
                instrument=instrument,
                price=new_price,
                timestamp=datetime.now()
            )
            
            # Broadcast to all subscribers (non-blocking)
            await self._broadcast_tick(instrument, tick)
    
    async def _broadcast_tick(self, instrument: str, tick: MarketTick):
        """Broadcast tick to all subscribers"""
        dead_queues = set()
        
        for queue in self.subscribers[instrument].copy():
            try:
                # Non-blocking put with timeout
                await asyncio.wait_for(queue.put(tick), timeout=0.1)
            except asyncio.TimeoutError:
                logger.warning(f"Queue full for {instrument}, skipping tick")
            except Exception as e:
                logger.error(f"Error broadcasting tick: {e}")
                dead_queues.add(queue)
        
        # Clean up dead queues
        for queue in dead_queues:
            self.subscribers[instrument].discard(queue)
    
    def get_current_price(self, instrument: str) -> float:
        """Get current price for an instrument"""
        return self.current_prices.get(instrument, 0.0)
    
