"""
Newsletter Parser - Extracts and structures content from newsletter emails
"""

import re
import logging
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import html

logger = logging.getLogger(__name__)

class NewsletterParser:
    """Parser for extracting structured content from newsletter emails."""
    
    def __init__(self):
        """Initialize the newsletter parser."""
        self.common_newsletter_patterns = [
            # Common newsletter indicators
            r'unsubscribe',
            r'newsletter',
            r'digest',
            r'weekly\s+update',
            r'daily\s+brief',
            r'roundup',
            r'view\s+in\s+browser'
        ]
        
        # Patterns for extracting articles/links
        self.article_patterns = [
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
            r'https?://[^\s<>"\']+',
        ]
    
    async def parse_newsletter(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse newsletter email and extract structured content."""
        try:
            parsed_content = {
                'email_id': email_data.get('id'),
                'subject': email_data.get('subject', ''),
                'sender': email_data.get('sender', ''),
                'date': email_data.get('date'),
                'is_newsletter': await self._is_newsletter(email_data),
                'articles': [],
                'summary': '',
                'links': [],
                'categories': [],
                'raw_text': ''
            }
            
            body = email_data.get('body', '')
            if not body:
                body = email_data.get('snippet', '')
            
            # Clean and extract text
            clean_text = await self._clean_html(body)
            parsed_content['raw_text'] = clean_text
            
            # Extract articles and links
            if parsed_content['is_newsletter']:
                parsed_content['articles'] = await self._extract_articles(body, clean_text)
                parsed_content['links'] = await self._extract_links(body)
                parsed_content['categories'] = await self._categorize_content(clean_text)
                parsed_content['summary'] = await self._generate_summary(clean_text)
            
            return parsed_content
            
        except Exception as e:
            logger.error(f"Error parsing newsletter: {e}")
            return {
                'email_id': email_data.get('id'),
                'error': str(e),
                'is_newsletter': False
            }
    
    async def _is_newsletter(self, email_data: Dict[str, Any]) -> bool:
        """Determine if email is likely a newsletter."""
        try:
            subject = email_data.get('subject', '').lower()
            sender = email_data.get('sender', '').lower()
            body = email_data.get('body', '').lower()
            snippet = email_data.get('snippet', '').lower()
            
            # Check for newsletter indicators
            newsletter_score = 0
            
            # Subject line indicators
            subject_indicators = [
                'newsletter', 'digest', 'weekly', 'daily', 'update',
                'roundup', 'briefing', 'summary', 'bulletin', 'dispatch'
            ]
            for indicator in subject_indicators:
                if indicator in subject:
                    newsletter_score += 2
            
            # Sender indicators
            sender_indicators = [
                'newsletter', 'noreply', 'no-reply', 'digest', 'updates'
            ]
            for indicator in sender_indicators:
                if indicator in sender:
                    newsletter_score += 1
            
            # Body/snippet indicators
            body_text = (body + ' ' + snippet).lower()
            body_indicators = [
                'unsubscribe', 'view in browser', 'forward to a friend',
                'newsletter', 'mailing list', 'weekly update', 'daily brief'
            ]
            for indicator in body_indicators:
                if indicator in body_text:
                    newsletter_score += 1
            
            # High link density suggests newsletter
            if body:
                link_count = len(re.findall(r'https?://', body))
                text_length = len(body)
                if text_length > 0 and (link_count / text_length) > 0.01:
                    newsletter_score += 1
            
            return newsletter_score >= 3
            
        except Exception as e:
            logger.error(f"Error checking if newsletter: {e}")
            return False
    
    async def _clean_html(self, html_content: str) -> str:
        """Clean HTML content and extract readable text."""
        try:
            if not html_content:
                return ""
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Decode HTML entities
            text = html.unescape(text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error cleaning HTML: {e}")
            return html_content
    
    async def _extract_articles(self, html_content: str, clean_text: str) -> List[Dict[str, Any]]:
        """Extract article information from newsletter."""
        try:
            articles = []
            
            if not html_content:
                return articles
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all links that might be articles
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Skip if no meaningful text or href
                if not text or len(text) < 10 or not href.startswith('http'):
                    continue
                
                # Skip common non-article links
                skip_patterns = [
                    'unsubscribe', 'view.*browser', 'forward', 'share',
                    'facebook', 'twitter', 'linkedin', 'instagram',
                    'privacy', 'terms', 'contact', 'about'
                ]
                
                if any(re.search(pattern, text.lower()) for pattern in skip_patterns):
                    continue
                
                # Extract context (surrounding text)
                context = ""
                parent = link.parent
                if parent:
                    context = parent.get_text(strip=True)[:200]
                
                article = {
                    'title': text,
                    'url': href,
                    'context': context,
                    'domain': urlparse(href).netloc
                }
                
                articles.append(article)
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_articles = []
            for article in articles:
                if article['url'] not in seen_urls:
                    seen_urls.add(article['url'])
                    unique_articles.append(article)
            
            return unique_articles[:10]  # Limit to top 10 articles
            
        except Exception as e:
            logger.error(f"Error extracting articles: {e}")
            return []
    
    async def _extract_links(self, html_content: str) -> List[str]:
        """Extract all meaningful links from content."""
        try:
            if not html_content:
                return []
            
            # Find all URLs
            urls = re.findall(r'https?://[^\s<>"\']+', html_content)
            
            # Clean and filter URLs
            clean_urls = []
            for url in urls:
                # Remove trailing punctuation
                url = re.sub(r'[.,;!?]+$', '', url)
                
                # Skip tracking and unsubscribe links
                skip_patterns = [
                    'unsubscribe', 'utm_', 'tracking', 'pixel',
                    'facebook.com', 'twitter.com', 'linkedin.com'
                ]
                
                if not any(pattern in url.lower() for pattern in skip_patterns):
                    clean_urls.append(url)
            
            return list(set(clean_urls))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
            return []
    
    async def _categorize_content(self, text: str) -> List[str]:
        """Categorize newsletter content based on keywords."""
        try:
            categories = []
            text_lower = text.lower()
            
            # Define category keywords
            category_keywords = {
                'technology': ['tech', 'software', 'ai', 'artificial intelligence', 'machine learning', 'startup', 'app'],
                'business': ['business', 'market', 'economy', 'finance', 'investment', 'stock', 'revenue'],
                'crypto': ['crypto', 'bitcoin', 'blockchain', 'ethereum', 'defi', 'nft', 'web3'],
                'science': ['research', 'study', 'science', 'medical', 'health', 'discovery'],
                'politics': ['politics', 'government', 'policy', 'election', 'law', 'regulation'],
                'sports': ['sports', 'game', 'team', 'player', 'championship', 'tournament'],
                'entertainment': ['movie', 'music', 'celebrity', 'entertainment', 'show', 'album']
            }
            
            # Count keyword matches for each category
            category_scores = {}
            for category, keywords in category_keywords.items():
                score = sum(text_lower.count(keyword) for keyword in keywords)
                if score > 0:
                    category_scores[category] = score
            
            # Return top categories
            sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            categories = [cat for cat, score in sorted_categories[:3]]
            
            return categories
            
        except Exception as e:
            logger.error(f"Error categorizing content: {e}")
            return []
    
    async def _generate_summary(self, text: str) -> str:
        """Generate a brief summary of the newsletter content."""
        try:
            if not text or len(text) < 100:
                return ""
            
            # Simple extractive summary - get first few sentences
            sentences = re.split(r'[.!?]+', text)
            meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
            
            if not meaningful_sentences:
                return text[:200] + "..."
            
            # Take first 2-3 sentences, up to 300 characters
            summary = ""
            for sentence in meaningful_sentences[:3]:
                if len(summary + sentence) > 300:
                    break
                summary += sentence + ". "
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return text[:200] + "..." if text else ""
    
    async def extract_key_points(self, parsed_content: Dict[str, Any]) -> List[str]:
        """Extract key points from parsed newsletter content."""
        try:
            key_points = []
            
            # Extract from article titles
            for article in parsed_content.get('articles', []):
                title = article.get('title', '').strip()
                if title and len(title) > 10:
                    key_points.append(title)
            
            # Extract from summary
            summary = parsed_content.get('summary', '')
            if summary:
                # Split summary into sentences
                sentences = re.split(r'[.!?]+', summary)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence and len(sentence) > 15:
                        key_points.append(sentence)
            
            return key_points[:5]  # Limit to top 5 key points
            
        except Exception as e:
            logger.error(f"Error extracting key points: {e}")
            return []
