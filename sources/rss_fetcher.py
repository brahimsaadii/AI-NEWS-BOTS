"""
RSS feed fetcher for different news sources and niches.
"""

import asyncio
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RSSFetcher:
    """Fetches news from RSS feeds for specific niches."""
    
    # Default RSS feeds for different niches
    DEFAULT_SOURCES = {
        'tech': [
            'https://feeds.feedburner.com/TechCrunch',
            'https://www.theverge.com/rss/index.xml',
            'https://feeds.arstechnica.com/arstechnica/index',
            'https://www.wired.com/feed/rss',
        ],
        'crypto': [
            'https://coindesk.com/arc/outboundfeeds/rss/',
            'https://cointelegraph.com/rss',
            'https://decrypt.co/feed',
            'https://bitcoinmagazine.com/.rss/full/',
        ],
        'ai': [
            'https://venturebeat.com/category/ai/feed/',
            'https://www.artificialintelligence-news.com/feed/',
            'https://syncedreview.com/feed/',
        ],
        'general': [
            'https://feeds.bbci.co.uk/news/rss.xml',
            'https://feeds.npr.org/1001/rss.xml',
        ]
    }
    
    def __init__(self, niche: str, custom_sources: List[str] = None):
        """Initialize RSS fetcher for a specific niche."""
        self.niche = niche.lower()
        self.custom_sources = custom_sources or []
        self.sources = self._get_sources()
        self.last_fetch_time = None
    
    def _get_sources(self) -> List[str]:
        """Get RSS sources for the niche."""
        if self.custom_sources:
            return self.custom_sources
        
        return self.DEFAULT_SOURCES.get(self.niche, self.DEFAULT_SOURCES['general'])
    
    async def fetch_latest_articles(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Fetch latest articles from all sources."""
        all_articles = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for source_url in self.sources:
            try:
                articles = await self._fetch_from_source(source_url, cutoff_time)
                all_articles.extend(articles)
                await asyncio.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Error fetching from {source_url}: {e}")
                continue
        
        # Remove duplicates and sort by publication date
        unique_articles = self._deduplicate_articles(all_articles)
        sorted_articles = sorted(
            unique_articles, 
            key=lambda x: x.get('published_parsed', datetime.min.timetuple()),
            reverse=True
        )
        
        self.last_fetch_time = datetime.now()
        return sorted_articles[:10]  # Return top 10 latest articles
    
    async def _fetch_from_source(self, source_url: str, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Fetch articles from a single RSS source."""
        try:
            # Use requests to fetch feed with timeout
            response = requests.get(source_url, timeout=10, headers={
                'User-Agent': 'News Tweet Bot/1.0'
            })
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"Feed parsing issues for {source_url}: {feed.bozo_exception}")
            
            articles = []
            for entry in feed.entries:
                # Parse publication date
                published_time = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_time = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_time = datetime(*entry.updated_parsed[:6])
                
                # Skip old articles
                if published_time and published_time < cutoff_time:
                    continue
                
                # Extract article data
                article = {
                    'title': entry.get('title', '').strip(),
                    'link': entry.get('link', ''),
                    'summary': self._clean_summary(entry.get('summary', '')),
                    'published': entry.get('published', ''),
                    'published_parsed': entry.get('published_parsed'),
                    'source': feed.feed.get('title', source_url),
                    'source_url': source_url
                }
                
                # Only add if title exists
                if article['title']:
                    articles.append(article)
            
            logger.info(f"Fetched {len(articles)} articles from {source_url}")
            return articles
        
        except Exception as e:
            logger.error(f"Error fetching RSS from {source_url}: {e}")
            return []
    
    def _clean_summary(self, summary: str) -> str:
        """Clean and truncate summary text."""
        if not summary:
            return ""
        
        # Remove HTML tags (basic cleaning)
        import re
        clean_summary = re.sub(r'<[^>]+>', '', summary)
        
        # Truncate to reasonable length
        if len(clean_summary) > 300:
            clean_summary = clean_summary[:300] + "..."
        
        return clean_summary.strip()
    
    def _deduplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate articles based on title similarity."""
        seen_titles = set()
        unique_articles = []
        
        for article in articles:
            title = article.get('title', '').lower().strip()
            
            # Simple deduplication based on title
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_articles.append(article)
        
        return unique_articles
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get information about configured sources."""
        return {
            'niche': self.niche,
            'sources': self.sources,
            'source_count': len(self.sources),
            'last_fetch': self.last_fetch_time.isoformat() if self.last_fetch_time else None
        }
