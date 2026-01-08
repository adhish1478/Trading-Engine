# Trading Automation Engine

## Overview

This project implements a mini trading automation engine that simulates how platforms like Tradetron or Quantiply execute trading strategies in production. The system:

- Simulates live market data
- Runs multiple strategies concurrently
- Evaluates entry/exit conditions
- Enforces risk management continuously
- Handles failures in isolation
- Shuts down gracefully at market close
- Is fully configurable and containerized

The focus is on correctness, async design, isolation, and production readiness, not UI.

---

## Architecture Overview

The system consists of the following components:

### 1. Market Data Simulator

- Generates price ticks at a configurable interval
- Uses an async, non-blocking broadcast model
- Supports multiple subscribers per instrument
- Continues running even if strategies fail

### 2. Strategy Engine

- Runs each strategy as an isolated async task
- Subscribes to market data via queues
- Manages strategy lifecycle states:
  - `CREATED` → `OPEN` → `CLOSED` / `FORCE_CLOSED` / `FAILED`
- Ensures one strategy failure does not affect others

### 3. Condition Evaluator

- Safely evaluates entry and exit conditions
- Supports:
  - Comparisons: `>` `<` `>=` `<=` `==`
  - Logical operators: `AND`, `OR`
  - Variables: `price`, `time`
- Time is normalized to minutes since midnight for deterministic comparisons

### 4. Risk Management

- Continuously monitors PnL for open positions
- Enforces:
  - Max loss (`STOP_LOSS`)
  - Max profit (`TARGET_HIT`)
- Risk exits take priority over strategy exit conditions

### 5. Orchestration & Shutdown

- Graceful shutdown on:
  - Market close time
  - `SIGINT` / `SIGTERM`
- On shutdown:
  - Market feed stops
  - All open positions are force-closed
  - Tasks are cancelled safely
  - Final execution summary is printed

### 6. Observability

- Structured logging for:
  - Strategy start / entry / exit
  - Exit reasons
  - Errors
- Periodic health checks

---

## Strategy Definition

Strategies are defined in a JSON file (`strategies.json`).

**Example:**
```json
{
  "strategy_id": "S1",
  "instrument": "NIFTY",
  "entry_condition": "price > 20100",
  "exit_condition": "price < 20050 OR time >= 15:20",
  "quantity": 50,
  "max_loss": 2000,
  "max_profit": 3000
}
```

Each strategy maintains its own independent state and lifecycle.

---

## Configuration

All configuration is handled via environment variables.

**Key variables:**
```
MARKET_OPEN=00:15
MARKET_CLOSE=02:20
TICK_INTERVAL=1.0
PRICE_VOLATILITY=0.002
STRATEGIES_FILE=strategies.json
LOG_LEVEL=INFO
```

Configuration is validated at startup. The application fails fast if configuration is invalid.

---

## Running the Application

### Local (Python)
```bash
python main.py
```

### Docker

Build the image:
```bash
docker build -t trading-engine .
```

Run:
```bash
docker run --env-file .env trading-engine
```

### Docker Compose
```bash
docker compose up --build
```

---

## Health Monitoring

The engine periodically logs system health, including:

- Active strategies
- Total strategies
- Market feed status
- Current prices per instrument

**Example:**
```
[HEALTH] {
  'status': 'healthy',
  'active_strategies': 3,
  'total_strategies': 15,
  'market_feed_active': True
}
```

---

## Failure Handling & Isolation

- Each strategy runs in its own async task
- A strategy crash:
  - Is logged
  - Marks the strategy as `FAILED`
  - Does not crash the engine
- Market feed and other strategies continue unaffected

---

## Time Handling & Timezones

- Time-based conditions use minutes since midnight
- Docker containers run in UTC by default
- The container timezone is explicitly set to ensure consistent behavior
- Market close logic uses full datetime comparison to handle overnight sessions correctly

---

## Limitations & Future Improvements

This implementation is intentionally minimal. Possible enhancements include:

- Replacing `eval()` with an AST-based DSL parser
- Adding backtesting support
- Persisting trades and metrics
- Strategy pause/resume
- Prometheus-compatible metrics
- WebSocket-based market feed

---

## Summary

This project demonstrates:

- Asynchronous system design
- Strategy isolation and fault tolerance
- Continuous risk management
- Graceful shutdown handling
- Dockerized, configurable execution

It is designed to reflect real-world trading automation system behavior, not just a simulation script.