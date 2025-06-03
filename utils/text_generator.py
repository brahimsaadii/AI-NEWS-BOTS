"""
Text generator using OpenAI API to create tweet suggestions from news headlines.
"""

import openai
import os
import logging
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)

class TextGenerator:
    """Generates tweet suggestions using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize text generator with OpenAI API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.warning("OpenAI API key not provided. Tweet generation will use fallback method.")
    
    async def generate_tweets(self, headline: str, summary: str = "", link: str = "") -> List[str]:
        """Generate tweet suggestions from news headline and summary."""
        if not headline:
            return []
        
        # Try OpenAI first, fallback to template-based generation
        if self.api_key:
            tweets = await self._generate_with_openai(headline, summary, link)
            if tweets:
                return tweets
        
        # Fallback to template-based generation
        return self._generate_fallback_tweets(headline, link)
    
    async def _generate_with_openai(self, headline: str, summary: str, link: str) -> List[str]:
        """Generate tweets using OpenAI API."""
        try:
            # Prepare prompt
            prompt = self._create_prompt(headline, summary, link)
            
            # Make API call
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a social media expert who creates engaging tweets from news articles."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=400,
                    temperature=0.7,
                    n=1
                )
            )
            
            # Extract tweets from response
            content = response.choices[0].message.content.strip()
            tweets = self._parse_tweets_from_response(content)
            
            # Validate tweet lengths
            valid_tweets = [tweet for tweet in tweets if len(tweet) <= 280]
            
            logger.info(f"Generated {len(valid_tweets)} valid tweets using OpenAI")
            return valid_tweets[:3]  # Return max 3 tweets
        
        except Exception as e:
            logger.error(f"Error generating tweets with OpenAI: {e}")
            return []
    
    def _create_prompt(self, headline: str, summary: str, link: str) -> str:
        """Create prompt for OpenAI API."""
        prompt = f"""
Create 3 engaging Twitter/X posts based on this news article. Each tweet should be:
- Maximum 280 characters
- Engaging and informative
- Include relevant emojis
- Have a hook to grab attention
- Be suitable for a tech-savvy audience

News Headline: {headline}

"""
        
        if summary:
            prompt += f"Summary: {summary}\n\n"
        
        prompt += """
Format your response as:
1. [First tweet]
2. [Second tweet]
3. [Third tweet]

Make each tweet unique in style (e.g., question, statement, call-to-action).
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
    
    def _generate_fallback_tweets(self, headline: str, link: str) -> List[str]:
        """Generate tweets using template-based fallback method."""
        try:
            # Clean headline
            clean_headline = headline.strip()
            if len(clean_headline) > 200:
                clean_headline = clean_headline[:200] + "..."
            
            tweets = []
            
            # Template 1: Direct headline with emoji
            tweet1 = f"🚨 {clean_headline}"
            if len(tweet1) <= 280:
                tweets.append(tweet1)
            
            # Template 2: Question format
            tweet2 = f"📰 Have you seen this? {clean_headline}"
            if len(tweet2) <= 280:
                tweets.append(tweet2)
            
            # Template 3: Call to action
            tweet3 = f"💡 Breaking: {clean_headline}\n\nThoughts? 👇"
            if len(tweet3) <= 280:
                tweets.append(tweet3)
            
            logger.info(f"Generated {len(tweets)} fallback tweets")
            return tweets
        
        except Exception as e:
            logger.error(f"Error generating fallback tweets: {e}")
            return []
    
    def set_api_key(self, api_key: str):
        """Set OpenAI API key."""
        self.api_key = api_key
        openai.api_key = api_key
    
    def test_api_connection(self) -> bool:
        """Test if OpenAI API is working."""
        if not self.api_key:
            return False
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI API test failed: {e}")
            return False
