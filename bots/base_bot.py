"""
Base Bot Class - Abstract base for all bot types
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes

logger = logging.getLogger(__name__)

class BaseBot(ABC):
    """Abstract base class for all bot types."""
    
    def __init__(self, bot_config: Dict[str, Any]):
        """Initialize base bot with configuration."""
        self.config = bot_config
        self.bot_id = bot_config["id"]
        self.name = bot_config["name"]
        self.token = bot_config["token"]
        self.owner_id = bot_config["owner_id"]
        self.frequency = bot_config["frequency"]
        self.auto_post = bot_config.get("auto_post", False)
        self.x_credentials = bot_config.get("x_credentials", {})
        
        # Telegram bot setup
        self.application = Application.builder().token(self.token).build()
        self.running = False
        
        # Setup base handlers
        self._setup_base_handlers()
    
    def _setup_base_handlers(self):
        """Setup common handlers for all bots."""
        from telegram.ext import CommandHandler, CallbackQueryHandler
        
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    @abstractmethod
    async def fetch_content(self) -> List[Dict[str, Any]]:
        """Fetch content for this bot type. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def process_content(self, content: Dict[str, Any]) -> Optional[str]:
        """Process content and generate tweet text. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def get_bot_type(self) -> str:
        """Return the bot type identifier."""
        pass
    
    async def start(self):
        """Start the bot."""
        logger.info(f"Starting {self.get_bot_type()} bot: {self.name}")
        self.running = True
        
        # Start Telegram bot
        await self.application.initialize()
        await self.application.start()
        
        # Start the main processing loop
        asyncio.create_task(self._main_loop())
        
        # Start polling for Telegram updates
        await self.application.updater.start_polling()
    
    async def stop(self):
        """Stop the bot."""
        logger.info(f"Stopping {self.get_bot_type()} bot: {self.name}")
        self.running = False
        
        if self.application.updater:
            await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
    
    async def _main_loop(self):
        """Main processing loop for the bot."""
        while self.running:
            try:
                # Fetch new content
                content_items = await self.fetch_content()
                
                for content in content_items:
                    if not self.running:
                        break
                    
                    # Process content and generate tweet
                    tweet_text = await self.process_content(content)
                    
                    if tweet_text:
                        # Send to owner for approval or auto-post
                        await self._handle_tweet_suggestion(content, tweet_text)
                
                # Wait for next cycle
                if self.running:
                    await asyncio.sleep(self.frequency * 3600)  # Convert hours to seconds
                    
            except Exception as e:
                logger.error(f"Error in {self.get_bot_type()} bot main loop: {e}")
                if self.running:
                    await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _handle_tweet_suggestion(self, content: Dict[str, Any], tweet_text: str):
        """Handle tweet suggestion - either auto-post or ask for approval."""
        try:
            if self.auto_post and self.x_credentials:
                # Auto-post to X
                success = await self._post_to_x(tweet_text)
                if success:
                    await self._send_notification(
                        f"✅ Auto-posted tweet for {self.name}:\n\n{tweet_text}"
                    )
                else:
                    await self._send_tweet_for_approval(content, tweet_text)
            else:
                # Send for manual approval
                await self._send_tweet_for_approval(content, tweet_text)
                
        except Exception as e:
            logger.error(f"Error handling tweet suggestion: {e}")
            await self._send_notification(f"❌ Error processing tweet: {str(e)}")
    
    async def _send_tweet_for_approval(self, content: Dict[str, Any], tweet_text: str):
        """Send tweet suggestion to owner for approval."""
        keyboard = [
            [InlineKeyboardButton("✅ Post Tweet", callback_data=f"post_{self.bot_id}")],
            [InlineKeyboardButton("✏️ Edit Tweet", callback_data=f"edit_{self.bot_id}")],
            [InlineKeyboardButton("❌ Skip", callback_data=f"skip_{self.bot_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"🤖 **{self.name}** - {self.get_bot_type().title()} Bot\n\n"
            f"**Suggested Tweet:**\n{tweet_text}\n\n"
            f"**Source:** {content.get('title', 'N/A')}"
        )
        
        await self.application.bot.send_message(
            chat_id=self.owner_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _post_to_x(self, tweet_text: str) -> bool:
        """Post tweet to X/Twitter."""
        try:
            from utils.x_poster import XPoster
            
            x_poster = XPoster(self.x_credentials)
            result = await x_poster.post_tweet(tweet_text)
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Error posting to X: {e}")
            return False
    
    async def _send_notification(self, message: str):
        """Send notification to bot owner."""
        try:
            await self.application.bot.send_message(
                chat_id=self.owner_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        status_text = (
            f"🤖 **{self.name}** - {self.get_bot_type().title()} Bot\n\n"
            f"**Status:** {'🟢 Running' if self.running else '🔴 Stopped'}\n"
            f"**Update Frequency:** Every {self.frequency} hour(s)\n"
            f"**Auto-post:** {'✅ Enabled' if self.auto_post else '❌ Disabled'}\n"
            f"**X Integration:** {'✅ Connected' if self.x_credentials else '❌ Not configured'}"
        )
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            f"🤖 **{self.name}** - {self.get_bot_type().title()} Bot\n\n"
            f"**Commands:**\n"
            f"• /status - Show bot status\n"
            f"• /help - Show this help message\n\n"
            f"This bot monitors {self.get_bot_type()} content and suggests tweets every {self.frequency} hour(s)."
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith(f"post_{self.bot_id}"):
            # Extract tweet text from the message
            message_text = query.message.text
            if "**Suggested Tweet:**" in message_text:
                tweet_text = message_text.split("**Suggested Tweet:**")[1].split("**Source:**")[0].strip()
                
                success = await self._post_to_x(tweet_text)
                if success:
                    await query.edit_message_text(f"✅ Tweet posted successfully!\n\n{tweet_text}")
                else:
                    await query.edit_message_text(f"❌ Failed to post tweet. Please check your X credentials.\n\n{tweet_text}")
        
        elif data.startswith(f"skip_{self.bot_id}"):
            await query.edit_message_text("⏭️ Tweet suggestion skipped.")
        
        elif data.startswith(f"edit_{self.bot_id}"):
            await query.edit_message_text(
                "✏️ Tweet editing not implemented yet. Please use the X app to post manually:\n\n"
                f"{query.message.text.split('**Suggested Tweet:**')[1].split('**Source:**')[0].strip()}"
            )
