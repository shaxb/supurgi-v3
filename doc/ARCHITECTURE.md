# Supurgi-v3 Trading Bot Architecture

This document outlines the up-to-date folder structure for the Supurgi-v3 trading bot. Each module is designed to be modular, with a clear responsibility. For design concepts and architectural principles, see DESIGN_PRINCIPLES.md.

---

## Folder Structure

```
Supurgi-v3/
├── main.py                     # Application entry point; initializes and wires up modules.
├── requirements.txt            # Project dependencies.
├── orchestrator/               # Controls the main loop and module interactions.
│   └── orchestrator.py
├── config_manager/             # Loads and provides configuration data (API keys, params, risk, accounts, etc).
│   └── config_manager.py
├── data_feed/                  # Fetches and preprocesses market data (used by brokers).
│   └── data_feed.py
├── risk_manager/               # Implements risk management logic and trade approval.
│   └── risk_manager.py
├── brokers/                    # Handles trade execution (live or simulated, including backtesting logic).
│   ├── base_broker.py          # Abstract base class for broker interface.
│   ├── mt5_broker.py           # Implementation for MetaTrader 5.
│   └── simulated_broker.py     # Simulates trades and runs backtesting using historical data.
├── strategies/                 # Contains all trading strategies.
│   ├── base_strategy.py        # Abstract base class for strategies.
│   └── trend_following.py      # Example strategy.
├── trading/                    # Trade data structures and conversion utilities.
│   ├── trade.py                # Trade class: single source of truth for trade/order data.
│   └── trade_converter.py      # Converts Trade objects to/from external/legacy formats.
├── visualization/              # Creates visual reports and plots of trading performance.
│   └── visualizer.py
├── logging/                    # Logs events, trades, errors, and decisions.
│   └── logger.py
├── notifications/              # Sends alerts on critical events (e.g., via Telegram).
│   └── telegram_notifier.py
├── tests/                      # All tests for the application, mirroring the main structure.
│   ├── test_main.py
│   ├── orchestrator/
│   ├── config_manager/
│   ├── data_feed/
│   ├── risk_manager/
│   ├── brokers/
│   ├── strategies/
│   ├── trading/
│   ├── visualization/
│   ├── logging/
│   └── notifications/
└── data/                       # Static configuration and reference data.
    ├── symbol.json             # Tradable instrument configs.
    ├── risk.json               # Risk management parameters.
    ├── accounts.json           # Multiple trading account details.
    ├── controller.json         # Global bot settings (e.g., logging levels).
    └── symbol_meta.json        # Static metadata for each symbol (e.g., contract size, pip value, pip size, currency) used for risk, P&L, and position calculations by sim broker and risk manager.
```

---

## Module Roles
- **main.py:** Entry point, initializes orchestrator and modules.
- **orchestrator/**: Main loop, module orchestration, broker swapping.
- **config_manager/**: Loads and provides all configuration data.
- **data_feed/**: Fetches and preprocesses market data (used by brokers).
- **brokers/**: Executes trades (live or simulated), exposes unified interface. The simulated broker also handles all backtesting logic.
- **strategies/**: Generates trade signals, agnostic to execution mode.
- **risk_manager/**: Approves/rejects trades based on risk rules.
- **trading/**: Trade class and conversion utilities.
- **visualization/**: Plots and reports performance.
- **logging/**: Logs events, trades, and errors.
- **notifications/**: Sends alerts (e.g., Telegram).
- **tests/**: Mirrors main structure for comprehensive testing.
- **data/**: Static configuration and reference data.
