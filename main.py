"""
Supurgi-v3 Trading Bot - Main Entry Point

This is the main entry point for the Supurgi-v3 trading bot.
It initializes and wires up all modules, then starts the orchestrator.

The bot can be run in live or backtest mode depending on the configuration.
"""

import os
import sys
import traceback

def main():
    """
    Main entry point for the Supurgi-v3 trading bot.
    Initializes all modules and starts the orchestrator.
    """
    # Define the config directory
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')    # Initialize ConfigManager
    print("Initializing ConfigManager...")
    from config_manager.config_manager import ConfigManager
    config_manager = ConfigManager(config_dir)
    
    # Initialize Logger
    print("Initializing Logger...")
    from custom_logging.logger import Logger
    logger = Logger(config_manager)
    
    # Initialize Orchestrator
    print("Initializing Orchestrator...")
    from orchestrator.orchestrator import Orchestrator
    orchestrator = Orchestrator(config_manager, logger)
    
    try:
        # Initialize all components
        logger.log_info("Initializing Supurgi-v3 Trading Bot...")
        orchestrator.initialize()
        
        # Run the bot
        logger.log_info("Starting Supurgi-v3 Trading Bot...")
        orchestrator.run()
        
    except KeyboardInterrupt:
        print("\nBot execution interrupted by user")
        logger.log_info("Bot execution interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())
        logger.log_error("Fatal error in main", e)
        
        # Exit with error code
        sys.exit(1)
    finally:
        print("Supurgi-v3 Trading Bot stopped.")


if __name__ == "__main__":
    main()
