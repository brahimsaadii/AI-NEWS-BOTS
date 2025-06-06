"""
BotFather - Central controller for managing news tweet bots.
Handles bot creation, configuration, and lifecycle management.
"""

import asyncio
import json
import logging
import os
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
        
        # Document handler for Gmail credentials
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = """
🤖 **Welcome to BotFather News Tweet Manager!**

I help you create and manage specialized bots that generate tweet suggestions for your X (Twitter) account.

**Available Bot Types:**
📰 **RSS News Bot** - Monitors RSS feeds for news articles
📧 **Gmail Agent Bot** - Monitors Gmail newsletters and digests  
🌐 **Web Scraper Bot** - Scrapes websites for new content and articles
💼 **Job Monitor Bot** - Coming soon!

**Available Commands:**
• /addbot - Create a new specialized bot
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

**/addbot** - Create a new specialized bot
• Choose from RSS News Bot or Gmail Agent Bot
• I'll guide you through the setup process
• You'll need a Telegram bot token from @BotFather

**/listbots** - Show all your configured bots
• See which bots are running or stopped
• View bot types and configurations

**/deletebot** - Remove a bot permanently
• Stops the bot and deletes its configuration

**/startbot** - Start a stopped bot
• Begin news fetching and tweet generation

**/stopbot** - Stop a running bot
• Pause news fetching temporarily

**Bot Types:**
📰 **RSS News Bot** - Monitors RSS feeds for articles
• Fetches news from RSS feeds
• Configurable niches (Tech, Crypto, AI, etc.)
• Custom RSS feed sources supported

📧 **Gmail Agent Bot** - Monitors Gmail newsletters
• Scans Gmail for newsletter emails
• Extracts key content and articles
• Configurable sender and keyword filters
• Requires Gmail API credentials

**Common Features:**
• AI-powered tweet generation using OpenAI
• Manual or automatic posting to X/Twitter
• Configurable update frequency
• Smart content filtering and deduplication        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def addbot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the bot creation process."""
        user_id = update.effective_user.id
        self.user_states[user_id] = {"step": "bot_type"}
        
        # Show bot type selection buttons
        keyboard = [
            [InlineKeyboardButton("📰 RSS News Bot", callback_data="type_rss_news")],
            [InlineKeyboardButton("📧 Gmail Agent Bot", callback_data="type_gmail_agent")],
            [InlineKeyboardButton("🌐 Web Scraper Bot", callback_data="type_web_scraper")],
            [InlineKeyboardButton("💼 Job Monitor Bot", callback_data="type_job_monitor")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🚀 **Let's create your bot!**\n\n"
            "What type of bot would you like to create?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
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
                "Now I need the Telegram bot token. Go to @BotFather on Telegram, create a new bot, and paste the token here:"            )
        
        elif state["step"] == "bot_token":
            state["bot_token"] = text            # Handle different bot types
            if state.get("bot_type") == "gmail_agent":
                state["step"] = "gmail_setup"
                await update.message.reply_text(
                    "📧 **Gmail Agent Setup**\n\n"
                    "To monitor Gmail newsletters, I need you to upload your Gmail API credentials file.\n\n"
                    "Please follow the setup guide at: [Gmail Setup Instructions](GMAIL_SETUP.md)\n\n"
                    "After setting up your credentials, please send me the `credentials.json` file.",
                    parse_mode='Markdown'
                )
            elif state.get("bot_type") == "web_scraper":
                state["step"] = "web_scraper_websites"
                await update.message.reply_text(
                    "🌐 **Web Scraper Setup**\n\n"
                    "Please enter the websites you want to scrape (one per line).\n\n"
                    "Examples:\n"
                    "• https://techcrunch.com\n"
                    "• https://arstechnica.com\n"
                    "• https://www.theverge.com\n\n"
                    "Enter at least one website URL:"
                )
            elif state.get("bot_type") == "job_monitor":
                state["step"] = "job_monitor_queries"
                await update.message.reply_text(
                    "💼 **Job Monitor Setup**\n\n"
                    "Please enter job search queries (one per line).\n\n"
                    "Examples:\n"
                    "• Software Developer\n"
                    "• Data Scientist Python\n"
                    "• Frontend Engineer React\n"
                    "• Product Manager Remote\n\n"
                    "Enter at least one search query:"
                )
            else:
                # RSS News Bot flow
                state["step"] = "niche"
                
                # Show niche selection buttons
                keyboard = [
                    [InlineKeyboardButton("🔧 Technology", callback_data="niche_tech")],
                    [InlineKeyboardButton("💰 Cryptocurrency", callback_data="niche_crypto")],
                    [InlineKeyboardButton("🤖 Artificial Intelligence", callback_data="niche_ai")],
                    [InlineKeyboardButton("📰 General News", callback_data="niche_general")],
                    [InlineKeyboardButton("✏️ Custom Niche", callback_data="niche_custom")]                ]
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
            state["step"] = "x_credentials"
            await self._ask_x_credentials(update)
        
        elif state["step"] == "x_bearer_token":
            if text.lower() == "skip":
                state["x_credentials"] = {}
            else:
                state["x_credentials"] = {"bearer_token": text.strip()}
            state["step"] = "auto_post"
            await self._ask_auto_post(update)
        
        elif state["step"] == "x_api_key":
            state["x_credentials"] = state.get("x_credentials", {})
            state["x_credentials"]["api_key"] = text.strip()
            state["step"] = "x_api_secret"
            await update.message.reply_text("Please enter your X API Secret:")
        
        elif state["step"] == "x_api_secret":
            state["x_credentials"]["api_secret"] = text.strip()
            state["step"] = "x_access_token"
            await update.message.reply_text("Please enter your X Access Token:")
        
        elif state["step"] == "x_access_token":
            state["x_credentials"]["access_token"] = text.strip()
            state["step"] = "x_access_token_secret"
            await update.message.reply_text("Please enter your X Access Token Secret:")
        
        elif state["step"] == "x_access_token_secret":
            state["x_credentials"]["access_token_secret"] = text.strip()
            state["step"] = "auto_post"
            await self._ask_auto_post(update)
        
        # Gmail-specific steps
        elif state["step"] == "gmail_sender_filter":
            state["gmail_sender_filter"] = text.strip()
            state["step"] = "gmail_keyword_filter"
            await update.message.reply_text(
                "📌 **Keyword Filter (Optional)**\n\n"
                "Enter keywords to filter newsletters (comma-separated).\n"
                "Only emails containing these keywords will be processed.\n\n"
                "Examples: 'newsletter, digest, weekly, news'\n"
                "Or type 'skip' to process all newsletters:"
            )
        
        elif state["step"] == "gmail_keyword_filter":
            if text.lower() == "skip":
                state["gmail_keyword_filter"] = ""
            else:
                state["gmail_keyword_filter"] = text.strip()
            state["step"] = "frequency"
            await self._ask_frequency(update)
        
        # Web Scraper-specific steps
        elif state["step"] == "web_scraper_websites":
            websites = [url.strip() for url in text.split('\n') if url.strip()]
            if not websites:
                await update.message.reply_text("❌ Please enter at least one valid website URL.")
                return
            
            # Store websites with basic configuration
            state["web_scraper_websites"] = []
            for url in websites:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                state["web_scraper_websites"].append({
                    "url": url,
                    "name": url.replace('https://', '').replace('http://', '').split('/')[0],                    "method": "html"
                })
            
            state["step"] = "web_scraper_keywords"
            await update.message.reply_text(
                "🎯 **Keywords (Optional)**\n\n"
                "Enter keywords to filter articles (comma-separated).\n"
                "Only articles containing these keywords will be processed.\n\n"
                "Examples: 'AI, technology, innovation, startup'\n"
                "Or type 'skip' to process all articles:"
            )
        elif state["step"] == "web_scraper_keywords":
            if text.lower() == "skip":
                state["web_scraper_keywords"] = []
            else:
                state["web_scraper_keywords"] = [kw.strip() for kw in text.split(',') if kw.strip()]
            state["step"] = "frequency"
            await self._ask_frequency(update)
        
        # Job Monitor-specific steps
        elif state["step"] == "job_monitor_queries":
            queries = [query.strip() for query in text.split('\n') if query.strip()]
            if not queries:
                await update.message.reply_text("❌ Please enter at least one valid search query.")
                return
            
            state["job_monitor_queries"] = queries
            state["step"] = "job_monitor_location"
            await update.message.reply_text(
                "📍 **Location (Optional)**\n\n"
                "Enter a location to filter jobs geographically.\n\n"
                "Examples:\n"
                "• New York, NY\n"
                "• Remote\n"
                "• San Francisco\n"
                "• London, UK\n\n"
                "Or type 'skip' for any location:"
            )
        
        elif state["step"] == "job_monitor_location":
            if text.lower() == "skip":
                state["job_monitor_location"] = ""
            else:
                state["job_monitor_location"] = text.strip()
            state["step"] = "frequency"
            await self._ask_frequency(update)
            await self._ask_frequency(update)
        
        elif state["step"] == "x_access_token_secret":
            state["x_credentials"]["access_token_secret"] = text.strip()
            state["step"] = "auto_post"
            await self._ask_auto_post(update)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        # Debug logging
        logger.info(f"Button callback triggered: user_id={user_id}, data={data}")
        
        # Handle start/stop/delete buttons first (no user state required)
        if data.startswith("start_"):
            logger.info(f"Processing bot start command: {data}")
            bot_id = data.replace("start_", "")
            user_bots = self.config_manager.get_user_bots(query.from_user.id)
            if bot_id in user_bots:
                await query.edit_message_text(f"🚀 Starting bot: {user_bots[bot_id]['name']}...")
                await self._start_bot_process(bot_id, user_bots[bot_id])
                
                # Check if bot actually started
                if bot_id in self.bot_processes:
                    await query.edit_message_text(f"✅ Successfully started bot: {user_bots[bot_id]['name']}")
                else:
                    await query.edit_message_text(f"❌ Failed to start bot: {user_bots[bot_id]['name']}. Check logs for details.")
            else:
                await query.edit_message_text("❌ Bot not found.")
            return
        
        elif data.startswith("stop_"):
            logger.info(f"Processing bot stop command: {data}")
            bot_id = data.replace("stop_", "")
            user_bots = self.config_manager.get_user_bots(query.from_user.id)
            if bot_id in user_bots:
                await self._stop_bot_process(bot_id)
                await query.edit_message_text(f"⏹️ Stopped bot: {user_bots[bot_id]['name']}")
            else:
                await query.edit_message_text("❌ Bot not found.")
            return
        
        elif data.startswith("delete_"):
            logger.info(f"Processing bot delete command: {data}")
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
            return        # For bot creation flow - check if user has state
        if user_id not in self.user_states:
            logger.info(f"User {user_id} not in states, ignoring non-management callback")
            return
        
        state = self.user_states[user_id]
        
        # Handle bot type selection
        if data.startswith("type_"):
            bot_type = data.replace("type_", "")
            state["bot_type"] = bot_type
            state["step"] = "bot_name"
            
            type_names = {
                "rss_news": "RSS News Bot",
                "gmail_agent": "Gmail Agent Bot", 
                "web_scraper": "Web Scraper Bot",
                "job_monitor": "Job Monitor Bot"
            }
            
            await query.edit_message_text(
                f"Great! You've selected a **{type_names.get(bot_type, bot_type)}**.\n\n"
                "What would you like to name your bot?",
                parse_mode='Markdown'
            )
            return
        
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
                state["step"] = "x_credentials"
                await self._ask_x_credentials(query)
            else:
                state["use_default_sources"] = False
                state["step"] = "custom_sources"
                await query.edit_message_text(
                    "Please enter RSS feed URLs, one per line:\n\n"
                    "Example:\n"
                    "https://feeds.feedburner.com/TechCrunch\n"
                    "https://www.theverge.com/rss/index.xml"
                )
        
        elif data.startswith("x_"):
            x_type = data.replace("x_", "")
            if x_type == "bearer":
                state["step"] = "x_bearer_token"
                await query.edit_message_text(
                    "🔑 **Enter your X Bearer Token**\n\n"
                    "You can get this from the X Developer Portal:\n"
                    "1. Go to developer.twitter.com\n"
                    "2. Create an app or use existing one\n"
                    "3. Go to Keys and Tokens\n"
                    "4. Copy the Bearer Token\n\n"
                    "Paste your Bearer Token here, or type 'skip' to simulate tweets:",
                    parse_mode='Markdown'
                )
            elif x_type == "oauth":
                state["step"] = "x_api_key"
                await query.edit_message_text(
                    "🔐 **OAuth Setup - Step 1 of 4**\n\n"
                    "Please enter your X API Key:\n\n"
                    "(You can get these credentials from developer.twitter.com → Your App → Keys and Tokens)",
                    parse_mode='Markdown'
                )
            elif x_type == "skip":
                state["x_credentials"] = {}
                state["step"] = "auto_post"
                await self._ask_auto_post(query)
        
        elif data.startswith("auto_"):
            auto_post = data == "auto_yes"
            state["auto_post"] = auto_post
            await self._finalize_bot_creation(query)
    
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
        
        if hasattr(update_or_query, 'edit_message_text'):        await update_or_query.edit_message_text(text, reply_markup=reply_markup)
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
    
    async def _ask_x_credentials(self, update_or_query):
        """Ask for X (Twitter) credentials."""
        keyboard = [
            [InlineKeyboardButton("Bearer Token only", callback_data="x_bearer")],
            [InlineKeyboardButton("Full OAuth credentials", callback_data="x_oauth")],
            [InlineKeyboardButton("Skip (simulate tweets)", callback_data="x_skip")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """🐦 **X (Twitter) Account Setup**

To post tweets, I need your X API credentials. Choose your authentication method:

• **Bearer Token**: Simpler setup, good for basic posting
• **OAuth Credentials**: Full API access (requires API key, secret, access tokens)
• **Skip**: I'll simulate tweets (no actual posting)

Which option would you prefer?"""
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update_or_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
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
        
        # Create base bot configuration
        bot_config = {
            "name": state["bot_name"],
            "token": state["bot_token"],
            "bot_type": state.get("bot_type", "rss_news"),
            "frequency": state["frequency"],
            "auto_post": state["auto_post"],
            "x_credentials": state.get("x_credentials", {}),
            "owner_id": user_id,
            "active": False
        }        # Add type-specific configuration
        if state.get("bot_type") == "gmail_agent":
            # Save Gmail credentials to file
            credentials_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials")
            os.makedirs(credentials_dir, exist_ok=True)
            
            credentials_file = os.path.join(credentials_dir, f"gmail_credentials_{user_id}.json")
            with open(credentials_file, 'w') as f:
                json.dump(state["gmail_credentials"], f, indent=2)
            
            bot_config["gmail_config"] = {
                "credentials_file": credentials_file,
                "sender_filter": state.get("gmail_sender_filter", ""),
                "keyword_filter": state.get("gmail_keyword_filter", "")
            }
        elif state.get("bot_type") == "web_scraper":
            # Web Scraper configuration
            bot_config["scraper_config"] = {
                "websites": state.get("web_scraper_websites", []),
                "keywords": state.get("web_scraper_keywords", []),
                "content_filters": {
                    "min_content_length": 100,
                    "max_age_hours": 24
                }
            }
        elif state.get("bot_type") == "job_monitor":
            # Job Monitor configuration
            search_queries = []
            for query in state.get("job_monitor_queries", []):
                search_queries.append({
                    "query": query,
                    "location": state.get("job_monitor_location", ""),
                    "job_boards": ["indeed", "linkedin"],
                    "filters": {}
                })
            
            bot_config["job_config"] = {
                "search_queries": search_queries,
                "location": state.get("job_monitor_location", ""),
                "job_boards": ["indeed", "linkedin"],
                "filters": {
                    "max_age_days": 7,
                    "required_keywords": [],
                    "exclude_keywords": []
                }
            }
        else:
            # RSS News Bot configuration
            bot_config.update({
                "niche": state.get("niche", "general"),
                "use_default_sources": state.get("use_default_sources", True),
                "custom_sources": state.get("custom_sources", [])
            })
        
        # Save configuration
        bot_id = self.config_manager.add_bot(bot_config)
          # Clean up user state
        del self.user_states[user_id]
        
        # Get X credentials status for display
        x_creds = state.get("x_credentials", {})
        if x_creds.get("bearer_token"):
            x_status = "Bearer Token ✅"
        elif x_creds.get("api_key"):
            x_status = "OAuth Credentials ✅"
        else:
            x_status = "Simulation mode 🔄"
          # Create success message based on bot type
        bot_type = state.get("bot_type", "rss_news")
        
        if bot_type == "gmail_agent":
            success_text = f"""
✅ **Gmail Agent Bot '{state['bot_name']}' created successfully!**

**Configuration:**
• **Name:** {state['bot_name']}
• **Type:** Gmail Newsletter Monitor 📧
• **Update Frequency:** Every {state['frequency']} hour(s)
• **Auto-post:** {'Yes ✅' if state['auto_post'] else 'No (Manual approval) 👤'}
• **X Account:** {x_status}
• **Gmail Credentials:** Uploaded ✅
• **Sender Filter:** {state.get('gmail_sender_filter', 'All senders') or 'All senders'}
• **Keyword Filter:** {state.get('gmail_keyword_filter', 'No filter') or 'No filter'}
• **Bot ID:** {bot_id}

Your bot will monitor Gmail for newsletters and generate tweet suggestions!
Use /startbot to begin monitoring, or /listbots to see all your bots.
            """
        elif bot_type == "web_scraper":
            websites_list = ", ".join([w['name'] for w in state.get('web_scraper_websites', [])][:3])
            if len(state.get('web_scraper_websites', [])) > 3:
                websites_list += f" (+{len(state['web_scraper_websites']) - 3} more)"
            
            keywords_list = ", ".join(state.get('web_scraper_keywords', [])[:5])
            if len(state.get('web_scraper_keywords', [])) > 5:
                keywords_list += f" (+{len(state['web_scraper_keywords']) - 5} more)"
            
            success_text = f"""
✅ **Web Scraper Bot '{state['bot_name']}' created successfully!**

**Configuration:**
• **Name:** {state['bot_name']}
• **Type:** Web Content Scraper 🌐
• **Update Frequency:** Every {state['frequency']} hour(s)
• **Auto-post:** {'Yes ✅' if state['auto_post'] else 'No (Manual approval) 👤'}
• **X Account:** {x_status}
• **Websites:** {websites_list or 'None configured'}
• **Keywords:** {keywords_list or 'No filter'}
• **Bot ID:** {bot_id}

Your bot will scrape websites for new content and generate tweet suggestions!
Use /startbot to begin scraping, or /listbots to see all your bots.
            """
        elif bot_type == "job_monitor":
            queries_list = ", ".join(state.get('job_monitor_queries', [])[:3])
            if len(state.get('job_monitor_queries', [])) > 3:
                queries_list += f" (+{len(state['job_monitor_queries']) - 3} more)"
            
            location_text = state.get('job_monitor_location', '') or 'Any location'
            
            success_text = f"""
✅ **Job Monitor Bot '{state['bot_name']}' created successfully!**

**Configuration:**
• **Name:** {state['bot_name']}
• **Type:** Job Board Monitor 💼
• **Update Frequency:** Every {state['frequency']} hour(s)
• **Auto-post:** {'Yes ✅' if state['auto_post'] else 'No (Manual approval) 👤'}
• **X Account:** {x_status}
• **Search Queries:** {queries_list}
• **Location:** {location_text}
• **Job Boards:** Indeed, LinkedIn
• **Bot ID:** {bot_id}

Your bot will monitor job boards for new postings and generate tweet suggestions!
Use /startbot to begin job monitoring, or /listbots to see all your bots.
            """
        else:
            success_text = f"""
✅ **RSS News Bot '{state['bot_name']}' created successfully!**

**Configuration:**
• **Name:** {state['bot_name']}
• **Type:** RSS News Monitor 📰
• **Niche:** {state.get('niche', 'General').title()}
• **Update Frequency:** Every {state['frequency']} hour(s)
• **Auto-post:** {'Yes ✅' if state['auto_post'] else 'No (Manual approval) 👤'}
• **X Account:** {x_status}
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
        bot_list = "🤖 **Your Bots:**\n\n"
        for bot_id, config in bots.items():
            status = "🟢 Running" if config.get("active", False) else "🔴 Stopped"
            bot_type = config.get("bot_type", "rss_news")
              # Get type-specific emoji and details
            if bot_type == "gmail_agent":
                type_emoji = "📧"
                type_name = "Gmail Agent"
                details = f"• Monitoring: Gmail newsletters"
            elif bot_type == "web_scraper":
                type_emoji = "🌐"
                type_name = "Web Scraper"
                scraper_config = config.get("scraper_config", {})
                website_count = len(scraper_config.get("websites", []))
                details = f"• Monitoring: {website_count} website(s)"
            else:
                type_emoji = "📰"
                type_name = "RSS News"
                details = f"• Niche: {config.get('niche', 'General').title()}"
            
            bot_list += f"{type_emoji} **{config['name']}** (ID: {bot_id})\n"
            bot_list += f"• Type: {type_name}\n"
            bot_list += f"{details}\n"
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
        for bot_id, config in bots.items():        keyboard.append([InlineKeyboardButton(
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
            logger.info(f"Bot {bot_id} is already running")
            return  # Already running
        
        try:
            # Get the absolute path to the project directory
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
              # Determine bot script based on bot type
            bot_type = config.get("bot_type", "rss_news")
            if bot_type == "gmail_agent":
                bot_script = os.path.join(project_dir, "bots", "gmail_bot_runner.py")
            elif bot_type == "web_scraper":
                bot_script = os.path.join(project_dir, "bots", "web_scraper_bot_runner.py")
            else:
                bot_script = os.path.join(project_dir, "bots", "news_bot.py")
            
            # Verify bot script exists
            if not os.path.exists(bot_script):
                logger.error(f"Bot script not found: {bot_script}")
                return
            
            # Create logs directory if it doesn't exist
            logs_dir = os.path.join(project_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Prepare log files
            stdout_file = os.path.join(logs_dir, f"bot_{bot_id}_stdout.log")
            stderr_file = os.path.join(logs_dir, f"bot_{bot_id}_stderr.log")
            
            # Prepare environment variables for subprocess
            env = os.environ.copy()
            
            # Start the bot subprocess with proper working directory and environment
            with open(stdout_file, 'w') as stdout_f, open(stderr_file, 'w') as stderr_f:
                process = subprocess.Popen([
                    sys.executable, bot_script, bot_id
                ], 
                cwd=project_dir,
                env=env,
                stdout=stdout_f, 
                stderr=stderr_f,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
            
            # Wait a moment and verify the process started successfully
            await asyncio.sleep(2)
            
            if process.poll() is None:
                # Process is still running - success!
                self.bot_processes[bot_id] = process
                self.config_manager.update_bot_status(bot_id, True)
                logger.info(f"✅ Started bot process for {config['name']} (ID: {bot_id}) - PID: {process.pid}")
                logger.info(f"Bot logs: stdout={stdout_file}, stderr={stderr_file}")
            else:
                # Process exited immediately - error
                return_code = process.returncode
                logger.error(f"❌ Bot process {bot_id} exited immediately with code {return_code}")
                
                # Read error logs
                try:
                    with open(stderr_file, 'r') as f:
                        error_output = f.read()
                    if error_output:
                        logger.error(f"Bot {bot_id} stderr: {error_output}")
                except:
                    pass
                    
                try:
                    with open(stdout_file, 'r') as f:                    stdout_output = f.read()
                    if stdout_output:
                        logger.error(f"Bot {bot_id} stdout: {stdout_output}")
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Failed to start bot {bot_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _stop_bot_process(self, bot_id: str):
        """Stop a bot process."""
        if bot_id in self.bot_processes:
            process = self.bot_processes[bot_id]
            process.terminate()
            del self.bot_processes[bot_id]
            self.config_manager.update_bot_status(bot_id, False)
            logger.info(f"Stopped bot process for ID: {bot_id}")
    
    async def _auto_restart_active_bots(self):
        """Auto-restart any bots that were marked as active when BotFather was last shut down."""
        logger.info("Checking for active bots to auto-restart...")
        
        try:            # Get all active bots from configuration
            active_bots = self.config_manager.get_active_bots()
            
            if not active_bots:
                logger.info("No active bots found to restart")
                return
            
            logger.info(f"Found {len(active_bots)} active bots to restart")
            
            # Restart each active bot
            for bot_id, config in active_bots.items():
                logger.info(f"Auto-restarting bot: {config['name']} (ID: {bot_id})")
                await self._start_bot_process(bot_id, config)
                
                # Small delay between restarts to avoid overwhelming the system
                await asyncio.sleep(2)
            
            logger.info(f"Auto-restart completed. {len(self.bot_processes)} bots are now running.")
            
        except Exception as e:
            logger.error(f"Error during auto-restart: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _stop_all_bot_processes(self):
        """Stop all running bot processes during shutdown."""
        logger.info("Stopping all bot processes...")
        
        # Create a copy of the keys to avoid runtime dictionary modification issues
        bot_ids = list(self.bot_processes.keys())
        
        for bot_id in bot_ids:
            try:
                await self._stop_bot_process(bot_id)
                await asyncio.sleep(0.5)  # Small delay between stops
            except Exception as e:
                logger.error(f"Error stopping bot {bot_id}: {e}")
        
        logger.info("All bot processes stopped")
    
    async def start(self):
        """Start the BotFather application."""
        logger.info("Starting BotFather...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Auto-restart any active bots after BotFather startup
        await self._auto_restart_active_bots()
        
        # Keep the application running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            # Stop all bot processes before shutting down
            await self._stop_all_bot_processes()
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads (Gmail credentials)."""
        user_id = update.effective_user.id
        if user_id not in self.user_states:
            return
        
        state = self.user_states[user_id]
        
        if state["step"] == "gmail_setup":
            document = update.message.document
            
            # Check if it's a JSON file
            if not document.file_name.endswith('.json'):
                await update.message.reply_text(
                    "❌ Please upload a JSON file (credentials.json) from Google Cloud Console."
                )
                return
            
            try:
                # Download the file
                file = await context.bot.get_file(document.file_id)
                credentials_content = await file.download_as_bytearray()
                  # Validate JSON format
                credentials_data = json.loads(credentials_content.decode('utf-8'))
                
                # Check if it's a valid Google credentials file
                # Support both installed app and web app credential formats
                valid_credential = False
                if 'installed' in credentials_data:
                    # Desktop app credentials (most common)
                    installed = credentials_data['installed']
                    if 'client_id' in installed and 'client_secret' in installed:
                        valid_credential = True
                elif 'web' in credentials_data:
                    # Web app credentials
                    web = credentials_data['web']
                    if 'client_id' in web and 'client_secret' in web:
                        valid_credential = True
                elif 'client_id' in credentials_data and 'client_secret' in credentials_data:
                    # Direct format (less common)
                    valid_credential = True
                
                if not valid_credential:
                    await update.message.reply_text(
                        "❌ This doesn't appear to be a valid Google API credentials file. "
                        "Please make sure you downloaded the correct credentials.json file."
                    )
                    return
                
                # Save credentials to state (we'll save to file later)
                state["gmail_credentials"] = credentials_data
                state["step"] = "gmail_sender_filter"
                
                await update.message.reply_text(
                    "✅ **Gmail credentials uploaded successfully!**\n\n"
                    "📮 **Sender Filter (Optional)**\n\n"
                    "Enter email addresses or domains to monitor (comma-separated).\n"
                    "Only newsletters from these senders will be processed.\n\n"
                    "Examples:\n"
                    "• `newsletter@techcrunch.com, @substack.com`\n"
                    "• `updates@morning-brew.com`\n\n"
                    "Or type 'skip' to monitor all senders:",
                    parse_mode='Markdown'
                )
                
            except json.JSONDecodeError:
                await update.message.reply_text(
                    "❌ Invalid JSON file. Please upload a valid credentials.json file."
                )
            except Exception as e:
                logger.error(f"Error processing Gmail credentials: {e}")
                await update.message.reply_text(
                    "❌ Error processing the credentials file. Please try again."
                )
        else:
            await update.message.reply_text(
                "I'm not expecting a document right now. Please follow the setup flow."
            )
