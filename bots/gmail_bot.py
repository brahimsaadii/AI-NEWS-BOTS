"""
Gmail Agent Bot - Monitors Gmail for newsletters and generates tweets
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .base_bot import BaseBot
from utils.gmail_client import GmailClient
from utils.newsletter_parser import NewsletterParser
from utils.text_generator import TextGenerator

logger = logging.getLogger(__name__)

class GmailBot(BaseBot):
    """Gmail Agent Bot for monitoring newsletters and generating tweets."""
    
    def __init__(self, bot_config: Dict[str, Any]):
        """Initialize Gmail bot with configuration."""
        super().__init__(bot_config)
        
        # Gmail-specific configuration
        self.gmail_config = bot_config.get("gmail_config", {})
        self.sender_filters = self.gmail_config.get("sender_filters", [])
        self.subject_filters = self.gmail_config.get("subject_filters", [])
        self.keywords = self.gmail_config.get("keywords", [])
        self.last_check_time = datetime.now() - timedelta(hours=24)
        
        # Initialize Gmail client
        credentials_path = self.gmail_config.get("credentials_path", "")
        token_path = self.gmail_config.get("token_path", "")
        
        if not credentials_path or not token_path:
            logger.error(f"Gmail credentials not configured for bot {self.name}")
            self.gmail_client = None
        else:
            self.gmail_client = GmailClient(credentials_path, token_path)
        
        # Initialize parser and text generator
        self.parser = NewsletterParser()
        self.text_generator = TextGenerator()
        
        # Processed emails tracking
        self.processed_emails = set()
    
    def get_bot_type(self) -> str:
        """Return the bot type identifier."""
        return "gmail_agent"
    
    async def fetch_content(self) -> List[Dict[str, Any]]:
        """Fetch new newsletter emails from Gmail."""
        try:
            if not self.gmail_client:
                logger.error(f"Gmail client not configured for bot {self.name}")
                return []
            
            # Authenticate with Gmail
            if not await self.gmail_client.authenticate():
                logger.error(f"Gmail authentication failed for bot {self.name}")
                return []
            
            # Calculate hours since last check
            hours_back = max(1, int((datetime.now() - self.last_check_time).total_seconds() / 3600))
            
            # Fetch newsletter emails
            emails = await self.gmail_client.get_newsletter_emails(
                sender_filters=self.sender_filters,
                subject_filters=self.subject_filters,
                hours_back=hours_back
            )
            
            # Filter out already processed emails
            new_emails = [
                email for email in emails 
                if email.get('id') not in self.processed_emails
            ]
            
            # Update last check time
            self.last_check_time = datetime.now()
            
            logger.info(f"Gmail bot {self.name} found {len(new_emails)} new newsletter emails")
            
            # Parse newsletters and return content
            content_items = []
            for email in new_emails:
                parsed_content = await self.parser.parse_newsletter(email)
                
                # Only process if it's actually a newsletter
                if parsed_content.get('is_newsletter', False):
                    content_items.append(parsed_content)
                    self.processed_emails.add(email.get('id'))
                    
                    # Mark email as processed in Gmail
                    await self.gmail_client.add_label(email.get('id'), 'BotProcessed')
            
            return content_items
            
        except Exception as e:
            logger.error(f"Error fetching Gmail content for bot {self.name}: {e}")
            return []
    
    async def process_content(self, content: Dict[str, Any]) -> Optional[str]:
        """Process newsletter content and generate tweet text."""
        try:
            # Extract key information
            subject = content.get('subject', '')
            sender = content.get('sender', '')
            articles = content.get('articles', [])
            summary = content.get('summary', '')
            categories = content.get('categories', [])
            
            # Skip if no meaningful content
            if not articles and not summary:
                logger.info(f"No meaningful content in newsletter from {sender}")
                return None
            
            # Filter articles by keywords if specified
            if self.keywords:
                filtered_articles = []
                for article in articles:
                    title_lower = article.get('title', '').lower()
                    context_lower = article.get('context', '').lower()
                    
                    if any(keyword.lower() in title_lower or keyword.lower() in context_lower 
                           for keyword in self.keywords):
                        filtered_articles.append(article)
                
                articles = filtered_articles
            
            # Skip if no relevant articles after filtering
            if not articles and self.keywords:
                logger.info(f"No articles match keywords for bot {self.name}")
                return None
            
            # Generate tweet content
            tweet_context = {
                'type': 'newsletter',
                'source': 'Gmail Newsletter',
                'subject': subject,
                'sender': sender,
                'articles': articles[:3],  # Limit to top 3 articles
                'summary': summary,
                'categories': categories,
                'niche': getattr(self, 'niche', 'general')
            }
            
            tweet_text = await self.text_generator.generate_tweet(tweet_context)
            
            if tweet_text:
                logger.info(f"Generated tweet for newsletter from {sender}")
                return tweet_text
            else:
                logger.warning(f"Failed to generate tweet for newsletter from {sender}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing Gmail content: {e}")
            return None
    
    async def get_newsletter_stats(self) -> Dict[str, Any]:
        """Get statistics about processed newsletters."""
        try:
            if not self.gmail_client:
                return {}
            
            # Get recent emails for stats
            emails = await self.gmail_client.get_recent_emails(
                query="label:BotProcessed",
                max_results=50,
                hours_back=24 * 7  # Last week
            )
            
            # Process stats
            stats = {
                'total_processed': len(emails),
                'last_processed': None,
                'top_senders': {},
                'categories_count': {},
                'processed_today': 0
            }
            
            today = datetime.now().date()
            
            for email in emails:
                # Update last processed
                email_date = email.get('date')
                if email_date:
                    if not stats['last_processed'] or email_date > stats['last_processed']:
                        stats['last_processed'] = email_date
                    
                    # Count today's emails
                    if email_date.date() == today:
                        stats['processed_today'] += 1
                
                # Count senders
                sender = email.get('sender', 'Unknown')
                sender_domain = sender.split('@')[-1] if '@' in sender else sender
                stats['top_senders'][sender_domain] = stats['top_senders'].get(sender_domain, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting newsletter stats: {e}")
            return {}
    
    async def add_sender_filter(self, sender: str) -> bool:
        """Add a sender to the filter list."""
        try:
            if sender not in self.sender_filters:
                self.sender_filters.append(sender)
                # Update configuration would happen here
                logger.info(f"Added sender filter: {sender}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error adding sender filter: {e}")
            return False
    
    async def add_keyword_filter(self, keyword: str) -> bool:
        """Add a keyword to the filter list."""
        try:
            if keyword not in self.keywords:
                self.keywords.append(keyword)
                # Update configuration would happen here
                logger.info(f"Added keyword filter: {keyword}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error adding keyword filter: {e}")
            return False
    
    async def status_command(self, update, context):
        """Enhanced status command with Gmail-specific information."""
        try:
            # Get base status
            await super().status_command(update, context)
            
            # Add Gmail-specific status
            stats = await self.get_newsletter_stats()
            
            gmail_status = (
                f"\n**📧 Gmail Configuration:**\n"
                f"**Sender Filters:** {len(self.sender_filters)} configured\n"
                f"**Keyword Filters:** {len(self.keywords)} configured\n"
                f"**Newsletters Processed:** {stats.get('total_processed', 0)}\n"
                f"**Processed Today:** {stats.get('processed_today', 0)}\n"
                f"**Last Check:** {self.last_check_time.strftime('%Y-%m-%d %H:%M')}"
            )
            
            await update.message.reply_text(gmail_status, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in Gmail bot status command: {e}")
    
    async def help_command(self, update, context):
        """Enhanced help command with Gmail-specific information."""
        help_text = (
            f"🤖 **{self.name}** - Gmail Agent Bot\n\n"
            f"**What I do:**\n"
            f"• Monitor your Gmail for newsletters\n"
            f"• Extract key content and articles\n"
            f"• Generate relevant tweets\n"
            f"• Filter by senders and keywords\n\n"
            f"**Commands:**\n"
            f"• /status - Show detailed bot status\n"
            f"• /help - Show this help message\n\n"
            f"**Current Filters:**\n"
            f"• Sender Filters: {len(self.sender_filters)}\n"
            f"• Keyword Filters: {len(self.keywords)}\n\n"
            f"I check for new newsletters every {self.frequency} hour(s)."
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _handle_tweet_suggestion(self, content: Dict[str, Any], tweet_text: str):
        """Enhanced tweet handling with Gmail-specific context."""
        try:
            # Add Gmail context to the suggestion
            sender = content.get('sender', 'Unknown')
            subject = content.get('subject', 'No subject')
            articles_count = len(content.get('articles', []))
            
            # Call parent method with enhanced context
            enhanced_content = content.copy()
            enhanced_content['context_info'] = f"📧 From: {sender}\n📝 Subject: {subject}\n🔗 Articles: {articles_count}"
            
            await super()._handle_tweet_suggestion(enhanced_content, tweet_text)
            
        except Exception as e:
            logger.error(f"Error handling Gmail tweet suggestion: {e}")
    
    async def button_callback(self, update, context):
        """Enhanced button callback with Gmail-specific actions."""
        query = update.callback_query
        data = query.data
        
        # Handle Gmail-specific callbacks
        if data.startswith(f"gmail_stats_{self.bot_id}"):
            stats = await self.get_newsletter_stats()
            stats_text = (
                f"📊 **Newsletter Statistics**\n\n"
                f"**Total Processed:** {stats.get('total_processed', 0)}\n"
                f"**Processed Today:** {stats.get('processed_today', 0)}\n"
                f"**Last Processed:** {stats.get('last_processed', 'Never')}\n\n"
                f"**Top Senders:**\n"
            )
            
            for sender, count in list(stats.get('top_senders', {}).items())[:5]:
                stats_text += f"• {sender}: {count}\n"
            
            await query.edit_message_text(stats_text, parse_mode='Markdown')
            return
        
        # Call parent callback for other actions
        await super().button_callback(update, context)
