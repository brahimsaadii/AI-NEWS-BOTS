"""
Text generator using OpenAI API to create tweet suggestions from news headlines.
"""

from openai import OpenAI
import os
import logging
from typing import List, Optional
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class TextGenerator:
    """Generates tweet suggestions using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize text generator with OpenAI API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
        else:
            self.client = None
            logger.warning("OpenAI API key not provided. Tweet generation will require API key.")
    
    async def generate_tweets(self, headline: str, full_content: str = "", link: str = "") -> List[str]:
        """Generate tweet suggestions from news headline and full article content."""
        if not headline:
            return []
        
        # Only use OpenAI - no fallback templates
        if self.api_key and self.client:
            tweets = await self._generate_with_openai(headline, full_content, link)
            if tweets:
                return tweets
          # If no OpenAI key, return empty
        logger.warning("No OpenAI API key provided. Cannot generate tweets without API key.")
        return []
    
    async def _generate_with_openai(self, headline: str, full_content: str, link: str) -> List[str]:
        """Generate tweets using OpenAI API with full article content."""
        try:
            # Create simple prompt that gives full article to ChatGPT
            prompt = self._create_simple_prompt(headline, full_content, link)
            
            # Make API call using new client with timeout handling
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a social media expert who creates engaging tweets from news articles."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=400,
                        temperature=0.7
                    )
                ),
                timeout=30.0  # 30 second timeout for OpenAI API
            )            
            # Extract tweets from response
            content = response.choices[0].message.content.strip()
            tweets = self._parse_tweets_from_response(content)
            
            # Validate tweet lengths
            valid_tweets = [tweet for tweet in tweets if len(tweet) <= 280]
            
            logger.info(f"Generated {len(valid_tweets)} valid tweets using OpenAI")
            return valid_tweets[:3]  # Return max 3 tweets
            
        except asyncio.TimeoutError:
            logger.error("OpenAI API call timed out (30s)")
            return []
        except Exception as e:
            logger.error(f"Error generating tweets with OpenAI: {e}")
            return []
    
    def _create_simple_prompt(self, headline: str, full_content: str, link: str) -> str:
        """Create simple prompt that gives full article to ChatGPT."""
        prompt = f"""
Read this complete news article and create 3 engaging tweets about it.

ARTICLE HEADLINE: {headline}

FULL ARTICLE CONTENT:
{full_content}

INSTRUCTIONS:
- Read and analyze the ENTIRE article content above
- Create 3 unique, engaging tweets (max 270 characters each)
- Each tweet should show you understood the article deeply
- Include relevant hashtags and emojis
- Make tweets insightful and discussion-worthy
- DO NOT just copy sentences from the article
- Show expert analysis and commentary

Format your response as:
1. [First tweet]
2. [Second tweet]  
3. [Third tweet]
"""
        
        return prompt
    
    def _parse_tweets_from_response(self, content: str) -> List[str]:
        """Parse tweets from OpenAI response."""
        tweets = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for numbered lines
            if line and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                tweet = line[2:].strip()  # Remove number prefix
                if tweet:
                    tweets.append(tweet)
        
        return tweets
    
    # Legacy method for compatibility with other parts of the system
    def _analyze_article_content(self, headline_or_content: str, summary: str = "") -> dict:
        """Analyze article content - simplified since ChatGPT handles this now."""
        return {
            'impact': "This development signals significant changes in the technology landscape.",
            'insight': "Market dynamics suggest this is more than just another product announcement.",
            'future_question': "How will this reshape competitive dynamics in the coming months?",
            'sector': 'technology'
        }
