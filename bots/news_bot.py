"""
Individual news bot that fetches news and generates tweet suggestions.
Can be run as a standalone process with bot configuration.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from botfather.config_manager import ConfigManager
from sources.rss_fetcher import RSSFetcher
from utils.text_generator import TextGenerator
from utils.x_poster import XPoster

logger = logging.getLogger(__name__)

class NewsBot:
    def __init__(self, bot_id: str, config: Dict[str, Any]):
        """Initialize news bot with configuration."""
        self.bot_id = bot_id
        self.config = config
        self.token = config['token']
        self.application = Application.builder().token(self.token).build()
        
        # Initialize components
        self.rss_fetcher = RSSFetcher(config['niche'], config.get('custom_sources', []))
        self.text_generator = TextGenerator()
        self.x_poster = XPoster()
        
        # Setup scheduler
        self.scheduler = AsyncIOScheduler()
        
        # Track sent articles to avoid duplicates
        self.sent_articles = set()
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup command and callback handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("latest", self.latest_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = f"""
🤖 **{self.config['name']} is active!**

I'm your {self.config['niche']} news bot. I'll fetch the latest news and suggest tweets for you.

**Configuration:**
• **Update Frequency:** Every {self.config['frequency']} hour(s)
• **Auto-post:** {'Enabled ✅' if self.config['auto_post'] else 'Manual approval required 👤'}

**Commands:**
• /status - Check bot status
• /latest - Get latest news manually

I'll start sending you news updates automatically!
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status."""
        next_run = "Not scheduled"
        if self.scheduler.get_jobs():
            job = self.scheduler.get_jobs()[0]
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "Not scheduled"
        
        status_text = f"""
📊 **Bot Status**

• **Name:** {self.config['name']}
• **Niche:** {self.config['niche'].title()}
• **Status:** 🟢 Active
• **Next update:** {next_run}
• **Articles sent:** {len(self.sent_articles)}
• **Auto-post:** {'Yes ✅' if self.config['auto_post'] else 'No 👤'}
        """
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def latest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually fetch and send latest news."""
        await update.message.reply_text("🔍 Fetching latest news...")
        await self.fetch_and_send_news()
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("post_"):
            # Extract tweet index and article data
            parts = data.split("_", 2)
            tweet_index = int(parts[1])
            article_id = parts[2] if len(parts) > 2 else ""
            
            # Get the tweet text from the callback data or message
            # For now, we'll extract from the message text
            message_text = query.message.text
            
            # Extract the specific tweet option
            lines = message_text.split('\n')
            tweet_text = ""
            for i, line in enumerate(lines):
                if line.startswith(f"{tweet_index}."):
                    tweet_text = line[3:].strip()  # Remove number prefix
                    break
            
            if tweet_text:
                success = await self.x_poster.post_tweet(tweet_text)
                if success:
                    await query.edit_message_text(
                        f"✅ **Tweet posted successfully!**\n\n📱 Tweet: {tweet_text}",
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text(
                        f"❌ **Failed to post tweet.**\n\n🔧 Please check your X API configuration.",
                        parse_mode='Markdown'
                    )
            else:
                await query.edit_message_text("❌ Could not extract tweet text.")
        
        elif data == "skip":
            await query.edit_message_text("⏭️ **Skipped this article.**")
    
    async def fetch_and_send_news(self):
        """Fetch news and send tweet suggestions."""
        try:
            # Fetch latest articles
            articles = await self.rss_fetcher.fetch_latest_articles()
            
            if not articles:
                logger.info("No new articles found")
                return
            
            # Filter out already sent articles
            new_articles = [
                article for article in articles 
                if article.get('link') not in self.sent_articles
            ]
            
            if not new_articles:
                logger.info("No new articles to process")
                return
            
            # Process up to 3 articles per batch
            for article in new_articles[:3]:
                await self._process_article(article)
                self.sent_articles.add(article.get('link'))
                
                # Small delay between articles
                await asyncio.sleep(2)
        
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
    
    async def _process_article(self, article: Dict[str, Any]):
        """Process a single article and send tweet suggestions."""
        try:
            headline = article.get('title', '')
            link = article.get('link', '')
            summary = article.get('summary', '')
            
            # Generate tweet suggestions
            tweets = await self.text_generator.generate_tweets(headline, summary, link)
            
            if not tweets:
                logger.warning(f"No tweets generated for article: {headline}")
                return
            
            # Send to user
            await self._send_tweet_suggestions(article, tweets)
        
        except Exception as e:
            logger.error(f"Error processing article: {e}")
    
    async def _send_tweet_suggestions(self, article: Dict[str, Any], tweets: List[str]):
        """Send tweet suggestions to user."""
        headline = article.get('title', '')
        link = article.get('link', '')
        
        # Format message
        message_text = f"📰 **New article:** {headline}\n\n"
        message_text += "✍️ **Suggested Tweets:**\n\n"
        
        # Add numbered tweet options
        for i, tweet in enumerate(tweets, 1):
            message_text += f"{i}. {tweet}\n\n"
        
        # Create inline keyboard
        keyboard = []
        for i in range(len(tweets)):
            keyboard.append([InlineKeyboardButton(
                f"✅ Post {i+1}", 
                callback_data=f"post_{i+1}_{article.get('link', '')}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Skip", callback_data="skip")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send message to bot owner
        try:
            await self.application.bot.send_message(
                chat_id=self.config['owner_id'],
                text=message_text,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error sending message to user: {e}")
    
    def _schedule_news_fetching(self):
        """Schedule periodic news fetching."""
        frequency_hours = self.config['frequency']
        
        self.scheduler.add_job(
            func=self.fetch_and_send_news,
            trigger="interval",
            hours=frequency_hours,
            id=f"news_fetch_{self.bot_id}",
            replace_existing=True
        )
        
        logger.info(f"Scheduled news fetching every {frequency_hours} hours")
    
    async def start(self):
        """Start the news bot."""
        logger.info(f"Starting news bot: {self.config['name']}")
        
        # Initialize application
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Start scheduler
        self.scheduler.start()
        self._schedule_news_fetching()
        
        # Send initial news check
        await asyncio.sleep(5)  # Wait a bit for bot to be ready
        await self.fetch_and_send_news()
        
        try:
            # Keep running
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.scheduler.shutdown()
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

async def main():
    """Main function for running individual bot."""
    if len(sys.argv) < 2:
        print("Usage: python -m bots.news_bot <bot_id>")
        sys.exit(1)
    
    bot_id = sys.argv[1]
    
    # Load bot configuration
    config_manager = ConfigManager()
    config = config_manager.get_bot(bot_id)
    
    if not config:
        print(f"Bot configuration not found for ID: {bot_id}")
        sys.exit(1)
    
    # Create and start bot
    bot = NewsBot(bot_id, config)
    await bot.start()

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    asyncio.run(main())
