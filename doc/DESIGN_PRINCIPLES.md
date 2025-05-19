# Supurgi-v3 Trading Bot: Design Philosophy & Flow

This document summarizes the key architectural principles and design decisions for Supurgi-v3, based on practical experience and discussion. It is intended as a clear guide for all contributors and coding agents.

---

## 1. **Core Principles**
- **Modular, scalable, and maintainable**: Each component has a single responsibility and clear interface.
- **Strategy-agnostic execution**: Strategies do not know if they are running in live or backtest mode.
- **Consistent interfaces**: Brokers (live or simulated) expose the same API to strategies.
- **Config-driven**: All parameters, symbols, and risk rules are loaded from config files.
- **Test-first and robust**: All modules are tested and validated before live deployment.

---

## 2. **Bot Flow (Live & Backtest)**

1. **Startup**: `main.py` loads configuration and initializes the orchestrator.
2. **Data Fetch**: The broker (live or simulated) fetches data using `data_feed/`.
3. **Strategy Loop**:
    - Strategy requests latest market data from the broker.
    - Strategy processes data and generates a signal.
    - Signal is sent to the risk manager for approval.
    - If approved, the signal is sent to the broker for execution.
4. **Execution**:
    - In live mode, the broker places real trades.
    - In backtest mode, the simulated broker replays historical data and simulates trades.
5. **Logging & Notification**: All events, trades, and errors are logged. Critical events trigger notifications (e.g., Telegram).
6. **Visualization**: After backtest, results are sent to the visualizer for performance reporting.

---

## 3. **Backtesting Design**
- **Simulated broker** is responsible for replaying historical data and simulating order execution.
- **Strategies use the same interface** in both live and backtest modes.
- **No separate strategy code** for backtesting: only the broker is swapped.
- **Backtest ends** when historical data is exhausted; results are visualized and logged.

---

## 4. **Module Responsibilities**
- **main.py**: Entry point, initializes and wires up modules.
- **orchestrator/**: Controls the main loop and module interactions.
- **config_manager/**: Loads and provides configuration data.
- **data_feed/**: Fetches and preprocesses market data (used by brokers).
- **brokers/**: Executes trades (live or simulated).
- **strategies/**: Generates trade signals, agnostic to execution mode.
- **risk_manager/**: Approves or rejects trades based on risk rules.
- **trading/**: Trade data structures and utilities.
- **visualization/**: Plots and reports performance.
- **logging/**: Logs events and errors.
- **notifications/**: Sends alerts (e.g., Telegram).

---

## 5. **Best Practices**
- Keep modules decoupled and focused.
- Document interfaces and update this file as the architecture evolves.
- Test strategies in backtest before live deployment.
- Use version control and clear commit messages.

---

## 6. **Trade Data Consistency & Conversion**
- All modules must use the `Trade` class (defined in `trading/trade.py`) to represent and pass trade/order data.
- The `Trade` class contains all relevant fields (e.g., symbol, side, size, price, timestamps, status, etc.) and is the single source of truth for trade data structure.
- No raw dicts or legacy formats should be passed between core modules.
- If a broker, visualizer, or external API requires a different format, use `trade_converter` (in `trading/trade_converter.py`) to convert to/from the `Trade` class.
- This ensures consistency, extensibility, and reduces bugs from missing or misnamed fields.
- Any changes to trade data structure should be made in the `Trade` class and reflected in the converter as needed.

---

## 7. **Symbol & Strategy Configuration**
- Each symbol (e.g., EURUSDm) can have one or more strategies assigned, each with its own configuration and timeframe.
- The mapping of symbols to strategies and their parameters is defined in `data/symbol.json`.
- Example structure:

```json
{
  "EURUSDm": {
    "strategies": [
      {
        "name": "MA_Crossover",
        "timeframe": "H1",
        "fast_ma_period": 30,
        "slow_ma_period": 100
      },
      {
        "name": "MA_Crossover",
        "timeframe": "M15",
        "fast_ma_period": 10,
        "slow_ma_period": 50
      },
      {
        "name": "Breakout",
        "timeframe": "H4",
        "lookback": 20
      }
    ]
  },
  "USDJPY": {
    "strategies": [
      {
        "name": "MA_Crossover",
        "timeframe": "H1",
        "fast_ma_period": 20,
        "slow_ma_period": 80
      }
    ]
  }
}
```
- This allows flexible assignment and configuration of strategies per symbol, supporting multiple strategies or multiple configurations of the same strategy on different timeframes.
- The orchestrator and config_manager should parse this structure to initialize strategies accordingly.

---
**This document is the single source of truth for Supurgi-v3's architecture and design intent. All contributors and coding agents must follow these guidelines.**
