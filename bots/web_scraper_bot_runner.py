#!/usr/bin/env python3
# filepath: c:\Users\brahi\Desktop\ai-news-bots\bots\web_scraper_bot_runner.py
"""
Web Scraper Bot Runner - Standalone script to run a Web Scraper bot instance
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bots.web_scraper_bot import WebScraperBot
from botfather.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to run Web Scraper bot."""
    if len(sys.argv) != 2:
        logger.error("Usage: python web_scraper_bot_runner.py <bot_id>")
        sys.exit(1)
    
    bot_id = sys.argv[1]
    
    try:
        # Load bot configuration
        config_manager = ConfigManager()
        bot_config = config_manager.get_bot(bot_id)
        
        if not bot_config:
            logger.error(f"Bot configuration not found for ID: {bot_id}")
            sys.exit(1)
        
        # Verify this is a Web Scraper bot
        if bot_config.get("bot_type") != "web_scraper":
            logger.error(f"Bot {bot_id} is not a Web Scraper bot")
            sys.exit(1)
        
        logger.info(f"Starting Web Scraper bot: {bot_config['name']} (ID: {bot_id})")
        
        # Create and start the bot
        bot = WebScraperBot(bot_config)
        await bot.start()
        
        # Keep the bot running
        while bot.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running Web Scraper bot: {e}")
        sys.exit(1)
    finally:
        if 'bot' in locals():
            await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
