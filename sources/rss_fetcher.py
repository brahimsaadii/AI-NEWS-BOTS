"""
RSS feed fetcher for different news sources and niches.
"""

import asyncio
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from bs4 import BeautifulSoup
import re

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
        ],        'general': [
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
        
        logger.info(f"Fetching articles from {len(self.sources)} sources for niche: {self.niche}")
        logger.info(f"Looking for articles newer than: {cutoff_time}")
        
        for source_url in self.sources:
            try:
                articles = await self._fetch_from_source(source_url, cutoff_time)
                all_articles.extend(articles)
                logger.info(f"Fetched {len(articles)} articles from {source_url}")
                await asyncio.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Error fetching from {source_url}: {e}")
                continue
        
        logger.info(f"Total articles fetched: {len(all_articles)}")
        
        # Remove duplicates and sort by publication date
        unique_articles = self._deduplicate_articles(all_articles)
        sorted_articles = sorted(
            unique_articles, 
            key=lambda x: x.get('published_parsed', datetime.min.timetuple()),
            reverse=True
        )
        
        logger.info(f"After deduplication and sorting: {len(sorted_articles)} articles")
        
        self.last_fetch_time = datetime.now()
        final_articles = sorted_articles[:10]  # Return top 10 latest articles
        
        logger.info(f"Returning {len(final_articles)} latest articles")
        return final_articles
    
    async def _fetch_from_source(self, source_url: str, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Fetch articles from a single RSS source."""
        try:
            # Use requests to fetch feed with timeout and retries
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = requests.get(source_url, timeout=8, headers={
                        'User-Agent': 'News Tweet Bot/1.0'
                    })
                    response.raise_for_status()
                    break
                except (requests.Timeout, requests.ConnectionError) as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Retry {attempt + 1} for {source_url}: {e}")
                    await asyncio.sleep(1)  # Brief pause before retry
            
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
                  # Fetch full article content with timeout
                try:
                    full_content = await asyncio.wait_for(
                        self._fetch_full_article_content(article['link']),
                        timeout=10.0  # Reduced timeout for content fetching
                    )
                    if full_content:
                        article['content'] = full_content
                        logger.debug(f"Fetched full content for: {article['title'][:50]}...")
                    else:
                        # Fallback to summary if content fetch fails
                        article['content'] = article['summary']
                except asyncio.TimeoutError:
                    logger.warning(f"Content fetch timeout for: {article['title'][:50]}")
                    article['content'] = article['summary']
                except Exception as e:
                    logger.warning(f"Content fetch error for {article['title'][:50]}: {e}")
                    article['content'] = article['summary']
                
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
    
    async def _fetch_full_article_content(self, article_url: str) -> str:
        """Fetch the full text content of an article from its URL."""
        if not article_url:
            return ""
        
        try:
            # Set headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
              # Fetch the article page with reduced timeout
            response = requests.get(article_url, headers=headers, timeout=8)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
                element.decompose()
            
            # Try to find the main article content using common selectors
            content_selectors = [
                'article',
                '[role="main"]',
                '.post-content',
                '.article-content',
                '.entry-content',
                '.content',
                '.story-body',
                '.article-body',
                '.post-body',
                'main',
                '.main-content',
                '#content',
                '.article-text'
            ]
            
            article_content = None
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    # Get the largest element (likely the main content)
                    article_content = max(elements, key=lambda x: len(x.get_text()))
                    break
            
            # If no specific content area found, try to extract paragraphs
            if not article_content:
                paragraphs = soup.find_all('p')
                if len(paragraphs) >= 3:  # Ensure it's substantial content
                    article_content = soup
            
            if article_content:
                # Extract text and clean it
                text = article_content.get_text()
                
                # Clean up the text
                text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespace with single space
                text = re.sub(r'\n+', '\n', text)  # Replace multiple newlines with single newline
                text = text.strip()
                
                # Remove common footer text and navigation elements
                common_removals = [
                    r'subscribe to our newsletter.*',
                    r'sign up for.*newsletter.*',
                    r'follow us on.*',
                    r'share this article.*',
                    r'related articles.*',
                    r'recommended for you.*',
                    r'advertisement.*'
                ]
                
                for pattern in common_removals:
                    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                
                # Limit content length to avoid token limits
                if len(text) > 8000:  # Reasonable limit for GPT processing
                    text = text[:8000] + "..."
                
                logger.debug(f"Extracted {len(text)} characters from {article_url}")
                return text
            
            logger.warning(f"Could not extract content from {article_url}")
            return ""
            
        except Exception as e:
            logger.error(f"Error fetching full content from {article_url}: {e}")
            return ""

    def get_source_info(self) -> Dict[str, Any]:
        """Get information about configured sources."""
        return {
            'niche': self.niche,
            'sources': self.sources,
            'source_count': len(self.sources),
            'last_fetch': self.last_fetch_time.isoformat() if self.last_fetch_time else None
        }
