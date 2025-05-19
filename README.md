# Supurgi-v3 Trading Bot

Supurgi-v3 is a modular, extensible trading bot designed for live trading and backtesting with a unified strategy interface.

## Core Features

- Strategy-agnostic execution (same code for live trading and backtesting)
- Modular architecture with clear separation of concerns
- Config-driven operation for symbols, risk rules, and account management
- Comprehensive logging and visualization capabilities
- Support for multiple brokers including MetaTrader 5

## Project Structure

This project follows a carefully designed architecture to promote modularity, maintainability, and clean code.

For details on the folder structure and module responsibilities, see [ARCHITECTURE.md](doc/ARCHITECTURE.md).

For design principles, data flow, and best practices, see [DESIGN_PRINCIPLES.md](doc/DESIGN_PRINCIPLES.md).

## Getting Started

1. Set up your configuration files in the `data/` directory
2. Configure your strategies in `data/symbol.json`
3. Run in backtest mode first to validate strategies
4. Deploy to live mode when ready

## Requirements

See `requirements.txt` for dependencies.
