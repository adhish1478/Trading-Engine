"""
Strategy Engine
Manages strategy lifecycle, evaluation, and risk management
Each strategy runs as an isolated async task
"""
import asyncio
from typing import List, Dict
from datetime import datetime

from models import Strategy, StrategyState, ExitReason, MarketTick, Order
from market_sim import MarketDataSimulator
from condition_eval import ConditionEvaluator
from logger import setup_logger, log_strategy_event

logger = setup_logger(__name__)

class StrategyEngine:
    """Manages and executes trading strategies"""
    
    def __init__(self, market_simulator: MarketDataSimulator):
        self.market_simulator = market_simulator
        self.strategies: List[Strategy] = []
        self.active_strategies: List[Strategy] = []
        self.strategy_tasks: Dict[str, asyncio.Task] = {}
        self.evaluator = ConditionEvaluator()
        
    async def run(self, strategies: List[Strategy]):
        """Run all strategies concurrently"""
        self.strategies = strategies
        
        logger.info(f"Starting {len(strategies)} strategies")
        
        # Create isolated task for each strategy
        for strategy in strategies:
            task = asyncio.create_task(
                self._run_strategy(strategy),
                name=f"strategy_{strategy.strategy_id}"
            )
            self.strategy_tasks[strategy.strategy_id] = task
            self.active_strategies.append(strategy)
        
        # Wait for all strategies to complete
        results = await asyncio.gather(*self.strategy_tasks.values(), return_exceptions=True)
        
        # Log any errors
        for strategy, result in zip(strategies, results):
            if isinstance(result, Exception):
                logger.error(f"Strategy {strategy.strategy_id} failed: {result}")
    
    async def _run_strategy(self, strategy: Strategy):
        """Run a single strategy (isolated task)"""
        queue = None
        
        try:
            # Subscribe to market data
            queue = self.market_simulator.subscribe(strategy.instrument)
            
            log_strategy_event(
                logger, strategy.strategy_id, "STARTED",
                instrument=strategy.instrument,
                entry=strategy.entry_condition,
                exit=strategy.exit_condition
            )
            
            # Main strategy loop
            async for tick in self._consume_market_data(queue):
                if tick is None:  # Market closed signal
                    break
                
                await self._evaluate_strategy(strategy, tick)
                
                if strategy.is_closed():
                    break
            
            # If still open at market close, force close
            if strategy.is_open():
                await self._force_close_strategy(strategy, ExitReason.MARKET_CLOSE)
            
        except asyncio.CancelledError:
            logger.info(f"[{strategy.strategy_id}] Task cancelled")
            if strategy.is_open():
                await self._force_close_strategy(strategy, ExitReason.MARKET_CLOSE)
            raise
        
        except Exception as e:
            logger.error(f"[{strategy.strategy_id}] Error: {e}", exc_info=True)
            strategy.mark_failed()
        
        finally:
            # Cleanup
            if queue:
                self.market_simulator.unsubscribe(strategy.instrument, queue)
            
            if strategy in self.active_strategies:
                self.active_strategies.remove(strategy)
    
    async def _consume_market_data(self, queue: asyncio.Queue):
        """Async generator to consume market data"""
        while True:
            try:
                tick = await asyncio.wait_for(queue.get(), timeout=5.0)
                if tick is None:  # Stop signal
                    break
                yield tick
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error consuming market data: {e}")
                break
    
    async def _evaluate_strategy(self, strategy: Strategy, tick: MarketTick):
        """Evaluate strategy conditions and risk management"""
        
        # CREATED state - check entry condition
        if strategy.state == StrategyState.CREATED:
            if self.evaluator.evaluate(strategy.entry_condition, tick.price):
                await self._enter_position(strategy, tick.price)
        
        # OPEN state - monitor risk and exit conditions
        elif strategy.state == StrategyState.OPEN:
            # Priority 1: Risk management (runs first)
            current_pnl = strategy.calculate_pnl(tick.price)
            
            # Check stop loss
            if current_pnl <= -strategy.max_loss:
                await self._exit_position(strategy, tick.price, ExitReason.STOP_LOSS)
                return
            
            # Check target profit
            if current_pnl >= strategy.max_profit:
                await self._exit_position(strategy, tick.price, ExitReason.TARGET_HIT)
                return
            
            # Priority 2: Exit condition
            if self.evaluator.evaluate(strategy.exit_condition, tick.price):
                await self._exit_position(strategy, tick.price, ExitReason.EXIT_CONDITION)
                return
    
    async def _enter_position(self, strategy: Strategy, price: float):
        """Execute entry order"""
        order = Order(
            strategy_id=strategy.strategy_id,
            instrument=strategy.instrument,
            side="BUY",
            quantity=strategy.quantity,
            price=price
        )
        
        strategy.enter(price)
        
        log_strategy_event(
            logger, strategy.strategy_id, "ENTRY",
            price=f"{price:.2f}",
            quantity=strategy.quantity
        )
    
    async def _exit_position(self, strategy: Strategy, price: float, reason: ExitReason):
        """Execute exit order"""
        order = Order(
            strategy_id=strategy.strategy_id,
            instrument=strategy.instrument,
            side="SELL",
            quantity=strategy.quantity,
            price=price
        )
        
        strategy.exit(price, reason)
        
        log_strategy_event(
            logger, strategy.strategy_id, "EXIT",
            price=f"{price:.2f}",
            reason=reason.value,
            pnl=f"{strategy.pnl:+.2f}"
        )
    
    async def _force_close_strategy(self, strategy: Strategy, reason: ExitReason):
        """Force close a strategy (e.g., at market close)"""
        if strategy.is_open():
            current_price = self.market_simulator.get_current_price(strategy.instrument)
            await self._exit_position(strategy, current_price, reason)
    
    async def force_close_all(self):
        """Force close all open strategies"""
        for strategy in self.active_strategies:
            if strategy.is_open():
                await self._force_close_strategy(strategy, ExitReason.MARKET_CLOSE)
    
    def get_statistics(self) -> Dict:
        """Get engine statistics"""
        total = len(self.strategies)
        completed = sum(1 for s in self.strategies if s.state == StrategyState.CLOSED)
        force_closed = sum(1 for s in self.strategies if s.state == StrategyState.FORCE_CLOSED)
        failed = sum(1 for s in self.strategies if s.state == StrategyState.FAILED)
        never_entered = sum(1 for s in self.strategies if s.state == StrategyState.CREATED)
        
        total_pnl = sum(s.pnl for s in self.strategies if s.pnl is not None)
        winners = sum(1 for s in self.strategies if s.pnl and s.pnl > 0)
        losers = sum(1 for s in self.strategies if s.pnl and s.pnl < 0)
        
        return {
            "total": total,
            "completed": completed,
            "force_closed": force_closed,
            "failed": failed,
            "never_entered": never_entered,
            "total_pnl": total_pnl,
            "winners": winners,
            "losers": losers
        }