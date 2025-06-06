"""
Web Scraper - Scrapes content from websites for news aggregation
"""

import asyncio
import logging
import re
import requests
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urlencode
from bs4 import BeautifulSoup
import feedparser
import time

logger = logging.getLogger(__name__)

class WebScraper:
    """Scrapes content from specified websites and extracts articles."""
    
    def __init__(self):
        """Initialize the web scraper."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Cache to avoid re-scraping same URLs
        self.scraped_urls = set()
        self.last_scrape_time = {}
        
        # Common article selectors (can be customized per site)
        self.article_selectors = {
            'title': [
                'h1', 'h2', '.headline', '.title', '.article-title',
                '[data-testid="headline"]', '.entry-title'
            ],
            'content': [
                '.article-content', '.post-content', '.entry-content',
                '.article-body', '.content', 'article p', '.story-body'
            ],
            'link': [
                'a[href]'
            ],
            'date': [
                'time', '.date', '.published', '.timestamp',
                '[datetime]', '.article-date'
            ]
        }
    
    async def scrape_website(self, url: str, scrape_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape a website for articles.
        
        Args:
            url: Website URL to scrape
            scrape_config: Configuration including selectors, filters, etc.
        """
        try:
            # Check if we've scraped this URL recently
            if self._should_skip_scrape(url, scrape_config.get('min_interval_hours', 1)):
                logger.info(f"Skipping {url} - scraped recently")
                return []
            
            # Determine scraping method
            scrape_type = scrape_config.get('type', 'html')
            
            if scrape_type == 'rss':
                articles = await self._scrape_rss_feed(url, scrape_config)
            elif scrape_type == 'sitemap':
                articles = await self._scrape_sitemap(url, scrape_config)
            else:
                articles = await self._scrape_html_page(url, scrape_config)
            
            # Update scrape time
            self.last_scrape_time[url] = datetime.now()
            
            # Filter and process articles
            filtered_articles = self._filter_articles(articles, scrape_config)
            
            logger.info(f"Scraped {len(filtered_articles)} articles from {url}")
            return filtered_articles
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return []
    
    async def _scrape_html_page(self, url: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape articles from an HTML page."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = []
            
            # Get custom selectors or use defaults
            title_selectors = config.get('selectors', {}).get('title', self.article_selectors['title'])
            content_selectors = config.get('selectors', {}).get('content', self.article_selectors['content'])
            link_selectors = config.get('selectors', {}).get('link', self.article_selectors['link'])
            
            # Find article containers
            article_containers = soup.find_all(config.get('article_container', 'article'))
            
            if not article_containers:
                # Fallback: look for common article patterns
                article_containers = soup.find_all(['article', '.post', '.entry', '.news-item'])
            
            for container in article_containers:
                article = self._extract_article_from_container(container, title_selectors, content_selectors, link_selectors, url)
                if article and article.get('title'):
                    articles.append(article)
            
            # If no containers found, try to extract from the whole page
            if not articles:
                article = self._extract_article_from_container(soup, title_selectors, content_selectors, link_selectors, url)
                if article and article.get('title'):
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping HTML from {url}: {e}")
            return []
    
    async def _scrape_rss_feed(self, url: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape articles from an RSS feed."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            articles = []
            
            for entry in feed.entries:
                article = {
                    'title': entry.get('title', '').strip(),
                    'link': entry.get('link', ''),
                    'summary': self._clean_text(entry.get('summary', '')),
                    'content': self._clean_text(entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''),
                    'published': entry.get('published', ''),
                    'author': entry.get('author', ''),
                    'source': feed.feed.get('title', url),
                    'source_url': url,
                    'scraped_at': datetime.now().isoformat()
                }
                
                # Parse publication date
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article['published_date'] = datetime(*entry.published_parsed[:6])
                
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping RSS from {url}: {e}")
            return []
    
    async def _scrape_sitemap(self, url: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape articles from a sitemap."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            articles = []
            
            # Extract URLs from sitemap
            urls = [loc.text for loc in soup.find_all('loc')]
            
            # Limit the number of URLs to scrape
            max_urls = config.get('max_urls_per_sitemap', 10)
            urls = urls[:max_urls]
            
            for page_url in urls:
                # Skip if not a valid article URL
                if not self._is_article_url(page_url, config):
                    continue
                
                # Scrape individual page
                page_articles = await self._scrape_html_page(page_url, config)
                articles.extend(page_articles)
                
                # Rate limiting
                await asyncio.sleep(0.5)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping sitemap from {url}: {e}")
            return []
    
    def _extract_article_from_container(self, container, title_selectors: List[str], 
                                       content_selectors: List[str], link_selectors: List[str], 
                                       base_url: str) -> Optional[Dict[str, Any]]:
        """Extract article data from a BeautifulSoup container."""
        article = {
            'title': '',
            'content': '',
            'summary': '',
            'link': '',
            'author': '',
            'published': '',
            'source_url': base_url,
            'scraped_at': datetime.now().isoformat()
        }
        
        # Extract title
        for selector in title_selectors:
            title_elem = container.select_one(selector)
            if title_elem:
                article['title'] = self._clean_text(title_elem.get_text())
                break
        
        # Extract content
        content_parts = []
        for selector in content_selectors:
            content_elems = container.select(selector)
            for elem in content_elems:
                text = self._clean_text(elem.get_text())
                if text and len(text) > 50:  # Only substantial content
                    content_parts.append(text)
        
        article['content'] = ' '.join(content_parts)
        article['summary'] = article['content'][:300] + '...' if len(article['content']) > 300 else article['content']
        
        # Extract link
        for selector in link_selectors:
            link_elem = container.select_one(selector)
            if link_elem and link_elem.get('href'):
                article['link'] = urljoin(base_url, link_elem['href'])
                break
        
        if not article['link']:
            article['link'] = base_url
        
        # Extract date
        date_elem = container.select_one('time, .date, .published, [datetime]')
        if date_elem:
            if date_elem.get('datetime'):
                article['published'] = date_elem['datetime']
            else:
                article['published'] = self._clean_text(date_elem.get_text())
        
        # Extract author
        author_elem = container.select_one('.author, .byline, [rel="author"]')
        if author_elem:
            article['author'] = self._clean_text(author_elem.get_text())
        
        return article if article['title'] else None
    
    def _filter_articles(self, articles: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter articles based on configuration."""
        filtered = []
        
        # Get filter criteria
        keywords = config.get('keywords', [])
        exclude_keywords = config.get('exclude_keywords', [])
        min_content_length = config.get('min_content_length', 100)
        max_age_hours = config.get('max_age_hours', 24)
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for article in articles:
            # Skip if already scraped
            if article.get('link') in self.scraped_urls:
                continue
            
            # Content length filter
            content = article.get('content', '')
            if len(content) < min_content_length:
                continue
            
            # Keyword filters
            if keywords:
                title_lower = article.get('title', '').lower()
                content_lower = content.lower()
                
                if not any(keyword.lower() in title_lower or keyword.lower() in content_lower 
                          for keyword in keywords):
                    continue
            
            # Exclude keywords
            if exclude_keywords:
                title_lower = article.get('title', '').lower()
                content_lower = content.lower()
                
                if any(keyword.lower() in title_lower or keyword.lower() in content_lower 
                       for keyword in exclude_keywords):
                    continue
            
            # Age filter (if published date is available)
            if article.get('published_date') and article['published_date'] < cutoff_time:
                continue
            
            # Add to scraped URLs cache
            self.scraped_urls.add(article.get('link'))
            
            filtered.append(article)
        
        return filtered
    
    def _should_skip_scrape(self, url: str, min_interval_hours: int) -> bool:
        """Check if we should skip scraping based on last scrape time."""
        if url not in self.last_scrape_time:
            return False
        
        last_scrape = self.last_scrape_time[url]
        time_diff = datetime.now() - last_scrape
        
        return time_diff.total_seconds() < (min_interval_hours * 3600)
    
    def _is_article_url(self, url: str, config: Dict[str, Any]) -> bool:
        """Check if URL looks like an article URL."""
        url_patterns = config.get('article_url_patterns', [
            r'/article/', r'/post/', r'/news/', r'/blog/',
            r'/\d{4}/\d{2}/', r'/story/', r'/press-release/'
        ])
        
        exclude_patterns = config.get('exclude_url_patterns', [
            r'/tag/', r'/category/', r'/author/', r'/search/',
            r'/page/', r'/feed/', r'\.(css|js|jpg|png|gif|pdf)$'
        ])
        
        # Check if URL matches article patterns
        if url_patterns:
            if not any(re.search(pattern, url, re.IGNORECASE) for pattern in url_patterns):
                return False
        
        # Check if URL matches exclude patterns
        if exclude_patterns:
            if any(re.search(pattern, url, re.IGNORECASE) for pattern in exclude_patterns):
                return False
        
        return True
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove HTML tags if any remain
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)\"\']+', '', text)
        
        return text.strip()
    
    def get_scraper_stats(self) -> Dict[str, Any]:
        """Get statistics about scraping activity."""
        return {
            'total_scraped_urls': len(self.scraped_urls),
            'active_sources': len(self.last_scrape_time),
            'last_scrape_times': {
                url: time.isoformat() for url, time in self.last_scrape_time.items()
            }
        }
