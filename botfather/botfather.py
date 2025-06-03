"""
BotFather - Central controller for managing news tweet bots.
Handles bot creation, configuration, and lifecycle management.
"""

import asyncio
import logging
import subprocess
import sys
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)

class BotFather:
    def __init__(self, token: str):
        """Initialize BotFather with Telegram token."""
        self.token = token
        self.application = Application.builder().token(token).build()
        self.config_manager = ConfigManager()
        self.user_states = {}  # Track conversation states
        self.bot_processes = {}  # Track running bot processes
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup command and callback handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("addbot", self.addbot_command))
        self.application.add_handler(CommandHandler("listbots", self.listbots_command))
        self.application.add_handler(CommandHandler("deletebot", self.deletebot_command))
        self.application.add_handler(CommandHandler("startbot", self.startbot_command))
        self.application.add_handler(CommandHandler("stopbot", self.stopbot_command))
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler for conversation states
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = """
🤖 **Welcome to BotFather News Tweet Manager!**

I help you create and manage Telegram bots that fetch news and suggest tweets for your X (Twitter) account.

**Available Commands:**
• /addbot - Create a new news bot
• /listbots - Show all your bots
• /deletebot - Delete a bot
• /startbot - Start a bot
• /stopbot - Stop a bot
• /help - Show this help message

Let's get started with /addbot!
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🔧 **BotFather Commands:**

**/addbot** - Create a new news bot
• I'll guide you through setting up a bot for a specific niche
• You'll need a Telegram bot token from @BotFather

**/listbots** - Show all your configured bots
• See which bots are running or stopped

**/deletebot** - Remove a bot permanently
• Stops the bot and deletes its configuration

**/startbot** - Start a stopped bot
• Begin news fetching and tweet generation

**/stopbot** - Stop a running bot
• Pause news fetching temporarily

**Bot Features:**
• Fetches news from RSS feeds
• Generates tweet suggestions using AI
• Manual or automatic posting to X/Twitter
• Configurable update frequency
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def addbot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the bot creation process."""
        user_id = update.effective_user.id
        self.user_states[user_id] = {"step": "bot_name"}
        
        await update.message.reply_text(
            "🚀 Let's create your news bot!\n\n"
            "First, what would you like to name your bot? (e.g., 'Tech News Bot', 'Crypto Updates')"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages based on user state."""
        user_id = update.effective_user.id
        if user_id not in self.user_states:
            return
        
        state = self.user_states[user_id]
        text = update.message.text.strip()
        
        if state["step"] == "bot_name":
            state["bot_name"] = text
            state["step"] = "bot_token"
            await update.message.reply_text(
                f"Great! Your bot will be called '{text}'.\n\n"
                "Now I need the Telegram bot token. Go to @BotFather on Telegram, create a new bot, and paste the token here:"
            )
        
        elif state["step"] == "bot_token":
            state["bot_token"] = text
            state["step"] = "niche"
            
            # Show niche selection buttons
            keyboard = [
                [InlineKeyboardButton("🔧 Technology", callback_data="niche_tech")],
                [InlineKeyboardButton("💰 Cryptocurrency", callback_data="niche_crypto")],
                [InlineKeyboardButton("🤖 Artificial Intelligence", callback_data="niche_ai")],
                [InlineKeyboardButton("📰 General News", callback_data="niche_general")],
                [InlineKeyboardButton("✏️ Custom Niche", callback_data="niche_custom")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Perfect! Token saved.\n\n"
                "What news niche should this bot focus on?",
                reply_markup=reply_markup
            )
        
        elif state["step"] == "custom_niche":
            state["niche"] = text
            state["step"] = "frequency"
            await self._ask_frequency(update)
        
        elif state["step"] == "custom_sources":
            state["custom_sources"] = [url.strip() for url in text.split('\n') if url.strip()]
            state["step"] = "auto_post"
            await self._ask_auto_post(update)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in self.user_states:
            return
        
        state = self.user_states[user_id]
        data = query.data
        
        if data.startswith("niche_"):
            niche = data.replace("niche_", "")
            if niche == "custom":
                state["step"] = "custom_niche"
                await query.edit_message_text("Please enter your custom niche (e.g., 'Gaming News', 'Health Tech'):")
            else:
                state["niche"] = niche
                state["step"] = "frequency"
                await query.edit_message_text(f"Selected niche: {niche.title()}")
                await self._ask_frequency(query)
        
        elif data.startswith("freq_"):
            frequency = data.replace("freq_", "")
            state["frequency"] = int(frequency)
            state["step"] = "sources"
            await self._ask_sources(query)
        
        elif data.startswith("sources_"):
            sources_type = data.replace("sources_", "")
            if sources_type == "default":
                state["use_default_sources"] = True
                state["step"] = "auto_post"
                await self._ask_auto_post(query)
            else:
                state["use_default_sources"] = False
                state["step"] = "custom_sources"
                await query.edit_message_text(
                    "Please enter RSS feed URLs, one per line:\n\n"                    "Example:\n"
                    "https://feeds.feedburner.com/TechCrunch\n"
                    "https://www.theverge.com/rss/index.xml"
                )
        
        elif data.startswith("auto_"):
            auto_post = data == "auto_yes"
            state["auto_post"] = auto_post
            await self._finalize_bot_creation(query)
        
        elif data.startswith("start_"):
            bot_id = data.replace("start_", "")
            user_bots = self.config_manager.get_user_bots(query.from_user.id)
            if bot_id in user_bots:
                await self._start_bot_process(bot_id, user_bots[bot_id])
                await query.edit_message_text(f"✅ Started bot: {user_bots[bot_id]['name']}")
            else:
                await query.edit_message_text("❌ Bot not found.")
        
        elif data.startswith("stop_"):
            bot_id = data.replace("stop_", "")
            user_bots = self.config_manager.get_user_bots(query.from_user.id)
            if bot_id in user_bots:
                await self._stop_bot_process(bot_id)
                await query.edit_message_text(f"⏹️ Stopped bot: {user_bots[bot_id]['name']}")
            else:
                await query.edit_message_text("❌ Bot not found.")
        
        elif data.startswith("delete_"):
            bot_id = data.replace("delete_", "")
            user_bots = self.config_manager.get_user_bots(query.from_user.id)
            if bot_id in user_bots:
                # Stop the bot first if it's running
                if bot_id in self.bot_processes:
                    await self._stop_bot_process(bot_id)
                
                # Delete the configuration
                self.config_manager.delete_bot(bot_id)
                await query.edit_message_text(f"🗑️ Deleted bot: {user_bots[bot_id]['name']}")
            else:
                await query.edit_message_text("❌ Bot not found.")
    
    async def _ask_frequency(self, update_or_query):
        """Ask for update frequency."""
        keyboard = [
            [InlineKeyboardButton("Every 1 hour", callback_data="freq_1")],
            [InlineKeyboardButton("Every 3 hours", callback_data="freq_3")],
            [InlineKeyboardButton("Every 6 hours", callback_data="freq_6")],
            [InlineKeyboardButton("Every 12 hours", callback_data="freq_12")],
            [InlineKeyboardButton("Once daily", callback_data="freq_24")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "How often should the bot check for news?"
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update_or_query.message.reply_text(text, reply_markup=reply_markup)
    
    async def _ask_sources(self, query):
        """Ask about news sources."""
        keyboard = [
            [InlineKeyboardButton("Use default sources", callback_data="sources_default")],
            [InlineKeyboardButton("Add custom RSS feeds", callback_data="sources_custom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Would you like to use default news sources for your niche, or add custom RSS feeds?",
            reply_markup=reply_markup
        )
    
    async def _ask_auto_post(self, update_or_query):
        """Ask about auto-posting preference."""
        keyboard = [
            [InlineKeyboardButton("Manual approval", callback_data="auto_no")],
            [InlineKeyboardButton("Auto-post tweets", callback_data="auto_yes")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "Should tweets be posted automatically or require your approval?"
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update_or_query.message.reply_text(text, reply_markup=reply_markup)
    
    async def _finalize_bot_creation(self, query):
        """Finalize bot creation and save configuration."""
        user_id = query.from_user.id
        state = self.user_states[user_id]
        
        # Create bot configuration
        bot_config = {
            "name": state["bot_name"],
            "token": state["bot_token"],
            "niche": state["niche"],
            "frequency": state["frequency"],
            "auto_post": state["auto_post"],
            "use_default_sources": state.get("use_default_sources", True),
            "custom_sources": state.get("custom_sources", []),
            "owner_id": user_id,
            "active": False
        }
        
        # Save configuration
        bot_id = self.config_manager.add_bot(bot_config)
        
        # Clean up user state
        del self.user_states[user_id]
        
        success_text = f"""
✅ **Bot '{state['bot_name']}' created successfully!**

**Configuration:**
• **Name:** {state['bot_name']}
• **Niche:** {state['niche'].title()}
• **Update Frequency:** Every {state['frequency']} hour(s)
• **Auto-post:** {'Yes ✅' if state['auto_post'] else 'No (Manual approval) 👤'}
• **Bot ID:** {bot_id}

Use /startbot to begin news fetching, or /listbots to see all your bots.
        """
        
        await query.edit_message_text(success_text, parse_mode='Markdown')
    
    async def listbots_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all user's bots."""
        user_id = update.effective_user.id
        bots = self.config_manager.get_user_bots(user_id)
        
        if not bots:
            await update.message.reply_text("You don't have any bots yet. Use /addbot to create one!")
            return
        
        bot_list = "🤖 **Your News Bots:**\n\n"
        for bot_id, config in bots.items():
            status = "🟢 Running" if config.get("active", False) else "🔴 Stopped"
            bot_list += f"**{config['name']}** (ID: {bot_id})\n"
            bot_list += f"• Niche: {config['niche'].title()}\n"
            bot_list += f"• Status: {status}\n"
            bot_list += f"• Frequency: Every {config['frequency']} hour(s)\n\n"
        
        await update.message.reply_text(bot_list, parse_mode='Markdown')
    
    async def startbot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start a specific bot."""
        user_id = update.effective_user.id
        bots = self.config_manager.get_user_bots(user_id)
        
        if not bots:
            await update.message.reply_text("You don't have any bots. Use /addbot to create one!")
            return
        
        # If bot ID provided as argument
        if context.args:
            bot_id = context.args[0]
            if bot_id in bots:
                await self._start_bot_process(bot_id, bots[bot_id])
                await update.message.reply_text(f"✅ Started bot: {bots[bot_id]['name']}")
            else:
                await update.message.reply_text("Bot ID not found. Use /listbots to see available bots.")
        else:
            # Show list of bots to start
            keyboard = []
            for bot_id, config in bots.items():
                if not config.get("active", False):
                    keyboard.append([InlineKeyboardButton(
                        f"▶️ {config['name']}", 
                        callback_data=f"start_{bot_id}"
                    )])
            
            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Select a bot to start:", reply_markup=reply_markup)
            else:
                await update.message.reply_text("All your bots are already running!")
    
    async def stopbot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop a specific bot."""
        user_id = update.effective_user.id
        bots = self.config_manager.get_user_bots(user_id)
        
        if not bots:
            await update.message.reply_text("You don't have any bots. Use /addbot to create one!")
            return
        
        # Show list of active bots to stop
        keyboard = []
        for bot_id, config in bots.items():
            if config.get("active", False):
                keyboard.append([InlineKeyboardButton(
                    f"⏹️ {config['name']}", 
                    callback_data=f"stop_{bot_id}"
                )])
        
        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Select a bot to stop:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("No bots are currently running.")
    
    async def deletebot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a bot permanently."""
        user_id = update.effective_user.id
        bots = self.config_manager.get_user_bots(user_id)
        
        if not bots:
            await update.message.reply_text("You don't have any bots to delete.")
            return
        
        keyboard = []
        for bot_id, config in bots.items():
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {config['name']}", 
                callback_data=f"delete_{bot_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ **Warning:** This will permanently delete the bot and its configuration.\n\nSelect a bot to delete:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _start_bot_process(self, bot_id: str, config: dict):
        """Start a bot process."""
        if bot_id in self.bot_processes:
            return  # Already running
        
        try:
            # Start the bot subprocess
            process = subprocess.Popen([
                sys.executable, "-m", "bots.news_bot", bot_id
            ], cwd=".")
            
            self.bot_processes[bot_id] = process
            self.config_manager.update_bot_status(bot_id, True)
            logger.info(f"Started bot process for {config['name']} (ID: {bot_id})")
        
        except Exception as e:
            logger.error(f"Failed to start bot {bot_id}: {e}")
    
    async def _stop_bot_process(self, bot_id: str):
        """Stop a bot process."""
        if bot_id in self.bot_processes:
            process = self.bot_processes[bot_id]
            process.terminate()
            del self.bot_processes[bot_id]
            self.config_manager.update_bot_status(bot_id, False)
            logger.info(f"Stopped bot process for ID: {bot_id}")
    
    async def start(self):
        """Start the BotFather application."""
        logger.info("Starting BotFather...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep the application running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
