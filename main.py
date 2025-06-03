#!/usr/bin/env python3
"""
Main entry point for the News Tweet Bots system.
Starts the BotFather controller bot.
"""

import asyncio
import logging
import os
from botfather.botfather import BotFather

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to start the BotFather bot."""
    logger.info("Starting BotFather controller...")
    
    # Get BotFather token from environment or prompt user
    botfather_token = os.getenv('BOTFATHER_TOKEN')
    if not botfather_token:
        botfather_token = input("Enter your BotFather Telegram bot token: ").strip()
    
    if not botfather_token:
        logger.error("BotFather token is required!")
        return
    
    # Initialize and start BotFather
    botfather = BotFather(botfather_token)
    await botfather.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down BotFather...")
    except Exception as e:
        logger.error(f"Error starting BotFather: {e}")
