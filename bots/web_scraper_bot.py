"""
Web Scraper Bot - Scrapes websites for news content and generates tweets
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .base_bot import BaseBot
from utils.web_scraper import WebScraper
from utils.text_generator import TextGenerator
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class WebScraperBot(BaseBot):
    """Web Scraper Bot for monitoring websites and generating tweets."""
    
    def __init__(self, bot_config: Dict[str, Any]):
        """Initialize Web Scraper bot with configuration."""
        super().__init__(bot_config)
        
        # Web scraper-specific configuration
        self.scraper_config = bot_config.get("scraper_config", {})
        self.websites = self.scraper_config.get("websites", [])
        self.keywords = self.scraper_config.get("keywords", [])
        self.content_filters = self.scraper_config.get("content_filters", {})
        self.last_scrape_time = datetime.now() - timedelta(hours=24)
        
        # Initialize web scraper
        self.web_scraper = WebScraper()
        
        # Initialize text generator
        self.text_generator = TextGenerator()
        
        # Processed content tracking
        self.processed_urls = set()
        
        logger.info(f"Web Scraper Bot initialized for {len(self.websites)} websites")
    
    def get_bot_type(self) -> str:
        """Return the bot type identifier."""
        return "web_scraper"
    
    async def fetch_content(self) -> List[Dict[str, Any]]:
        """Fetch new articles from configured websites."""
        try:
            if not self.websites:
                logger.warning(f"No websites configured for bot {self.name}")
                return []
            
            all_content = []
            
            # Scrape each configured website
            for website_config in self.websites:
                try:
                    url = website_config.get("url", "")
                    if not url:
                        logger.warning(f"No URL configured for website config: {website_config}")
                        continue
                    
                    logger.info(f"Scraping website: {url}")
                    
                    # Create scrape configuration
                    scrape_config = {
                        "method": website_config.get("method", "html"),
                        "selectors": website_config.get("selectors", {}),
                        "filters": {
                            "keywords": self.keywords,
                            "min_content_length": self.content_filters.get("min_content_length", 100),
                            "max_age_hours": self.content_filters.get("max_age_hours", 24),
                            **website_config.get("filters", {})
                        },
                        "rate_limit": website_config.get("rate_limit", 1.0)
                    }
                    
                    # Scrape the website
                    articles = await self.web_scraper.scrape_website(url, scrape_config)
                    
                    # Filter out already processed articles
                    new_articles = [
                        article for article in articles 
                        if article.get('url') not in self.processed_urls
                    ]
                    
                    # Add website source info
                    for article in new_articles:
                        article['source_website'] = url
                        article['source_name'] = website_config.get("name", urlparse(url).netloc)
                        self.processed_urls.add(article.get('url'))
                    
                    all_content.extend(new_articles)
                    logger.info(f"Found {len(new_articles)} new articles from {url}")
                    
                except Exception as e:
                    logger.error(f"Error scraping website {website_config.get('url', 'unknown')}: {str(e)}")
                    continue
            
            # Update last scrape time
            self.last_scrape_time = datetime.now()
            
            # Sort by publication date (newest first)
            all_content.sort(key=lambda x: x.get('date', datetime.min), reverse=True)
            
            logger.info(f"Web Scraper bot {self.name} found {len(all_content)} new articles total")
            return all_content
            
        except Exception as e:
            logger.error(f"Error in Web Scraper bot {self.name} fetch_content: {str(e)}")
            return []
    
    async def process_content(self, content: Dict[str, Any]) -> Optional[str]:
        """Process scraped content and generate tweet text."""
        try:
            # Extract key information
            title = content.get('title', '').strip()
            url = content.get('url', '')
            source_name = content.get('source_name', 'Web')
            article_content = content.get('content', '').strip()
            
            if not title or not url:
                logger.warning(f"Missing title or URL in content: {content}")
                return None
            
            # Prepare content for text generation
            processed_content = {
                'title': title,
                'content': article_content[:500] if article_content else title,  # Limit content length
                'url': url,
                'source': source_name,
                'type': 'web_article'
            }
            
            # Generate tweet text
            tweet_text = await self.text_generator.generate_tweet(processed_content)
            
            if tweet_text:
                logger.info(f"Generated tweet for article: {title[:50]}...")
                return tweet_text
            else:
                logger.warning(f"Failed to generate tweet for article: {title}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing content in Web Scraper bot {self.name}: {str(e)}")
            return None
    
    async def get_status_info(self) -> Dict[str, Any]:
        """Get current status information for this bot."""
        try:
            return {
                "type": self.get_bot_type(),
                "name": self.name,
                "running": self.running,
                "websites_count": len(self.websites),
                "keywords_count": len(self.keywords),
                "processed_urls_count": len(self.processed_urls),
                "last_scrape": self.last_scrape_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_scrape_time else "Never",
                "frequency": f"{self.frequency} hours",
                "auto_post": self.auto_post
            }
        except Exception as e:
            logger.error(f"Error getting status info for Web Scraper bot {self.name}: {str(e)}")
            return {}
    
    async def get_configuration_summary(self) -> str:
        """Get a human-readable configuration summary."""
        try:
            summary = f"🕷️ *Web Scraper Bot: {self.name}*\n\n"
            summary += f"📊 *Status:* {'Running' if self.running else 'Stopped'}\n"
            summary += f"⏰ *Frequency:* Every {self.frequency} hours\n"
            summary += f"🚀 *Auto-post:* {'Enabled' if self.auto_post else 'Disabled'}\n\n"
            
            summary += f"🌐 *Websites ({len(self.websites)}):*\n"
            for i, website in enumerate(self.websites[:5], 1):  # Show first 5
                name = website.get('name', website.get('url', 'Unknown'))
                method = website.get('method', 'html').upper()
                summary += f"  {i}. {name} ({method})\n"
            
            if len(self.websites) > 5:
                summary += f"  ... and {len(self.websites) - 5} more\n"
            
            if self.keywords:
                summary += f"\n🎯 *Keywords ({len(self.keywords)}):*\n"
                keyword_list = ", ".join(self.keywords[:10])  # Show first 10
                if len(self.keywords) > 10:
                    keyword_list += f" (+{len(self.keywords) - 10} more)"
                summary += f"  {keyword_list}\n"
            
            summary += f"\n📈 *Stats:*\n"
            summary += f"  • Processed URLs: {len(self.processed_urls)}\n"
            summary += f"  • Last scrape: {self.last_scrape_time.strftime('%Y-%m-%d %H:%M') if self.last_scrape_time else 'Never'}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating configuration summary for Web Scraper bot {self.name}: {str(e)}")
            return f"Error generating summary for {self.name}"
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test web scraping connection and return results."""
        try:
            if not self.websites:
                return {
                    "success": False,
                    "message": "No websites configured",
                    "details": {}
                }
            
            test_results = []
            
            # Test first website only for quick test
            website_config = self.websites[0]
            url = website_config.get("url", "")
            
            try:
                # Create minimal scrape config for testing
                scrape_config = {
                    "method": website_config.get("method", "html"),
                    "selectors": website_config.get("selectors", {}),
                    "filters": {
                        "max_age_hours": 168,  # 1 week for testing
                        "min_content_length": 50
                    },
                    "rate_limit": 2.0  # Slower for testing
                }
                
                # Test scrape
                articles = await self.web_scraper.scrape_website(url, scrape_config)
                
                test_results.append({
                    "url": url,
                    "success": True,
                    "articles_found": len(articles),
                    "method": scrape_config["method"]
                })
                
            except Exception as e:
                test_results.append({
                    "url": url,
                    "success": False,
                    "error": str(e),
                    "method": website_config.get("method", "html")
                })
            
            success = any(result["success"] for result in test_results)
            
            return {
                "success": success,
                "message": "Web scraping test completed",
                "details": {
                    "websites_tested": len(test_results),
                    "results": test_results
                }
            }
            
        except Exception as e:
            logger.error(f"Error testing Web Scraper bot connection: {str(e)}")
            return {
                "success": False,
                "message": f"Test failed: {str(e)}",
                "details": {}
            }
