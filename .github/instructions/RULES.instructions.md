---
applyTo: '**'
---

# AI Agent Coding Standards & Domain Guidelines

1. **Coding Style & Conventions**  
   - Follow [PEP 8](https://peps.python.org/pep-0008/) guidelines when writing Python code.  
   - Use clear, descriptive naming for functions, classes, and variables.  
   - Include docstrings for all public methods and classes.  

2. **Architecture & Design**  
   - Adhere strictly to the folder structure and module responsibilities in doc/ARCHITECTURE.md.  
   - Implement logic according to doc/DESIGN_PRINCIPLES.md, without introducing new modules or flows.  
   - Keep the code modular, with a single responsibility per module.  

3. **Trading Domain Knowledge**  
   - Assume a MetaTrader or simulated broker environment for fetching market data and executing trades.  
   - Use the Trade class (trading/trade.py) for all order/trade objects without passing raw dicts.  
   - For backtesting or live mode, maintain the same interfaces for strategies.  

4. **Configuration-Driven**  
   - Load symbol, strategy, risk, and account configurations from files in the data/ folder.  
   - Do not hardcode parameters that are meant to be configured (e.g., lot sizes, timeframes).  

5. **Error Handling & Logging**  
   - Use the designated logging system (logging/logger.py) rather than print statements.  
   - Handle exceptions gracefully; log errors with detail but don’t reveal sensitive info.  

6. **Testing & Validation**  
   - Provide unit tests mirroring the primary folder structure (tests/).  
   - Ensure new code is covered by tests, especially for risk-critical modules.  
   - Do not merge changes that break existing tests.  

7. **Updates & Communication**  
   - If uncertain about any requirement or design, ask for clarification before implementing.  
   - Document changes succinctly in commit messages, referencing relevant architectural sections.  
   - Avoid adding architectural concepts or design explanations to ARCHITECTURE.md—only update DESIGN_PRINCIPLES.md for conceptual changes.

By following these guidelines, you help maintain consistency, quality, and clarity across the entire Supurgi-v3 codebase.