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
        
        # Fallback to template-based generation with summary
        return self._generate_fallback_tweets_with_summary(headline, summary, link)
    
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
- Between 200-270 characters (informative but not too long)
- Include a meaningful summary of the key points, not just the headline
- Explain WHY this news matters or what the impact is
- Include relevant emojis and 2-3 strategic hashtags
- Have a hook to grab attention in the first line
- Be suitable for a tech-savvy audience
- End with "Read more:" followed by the article link
- Make each tweet self-contained and informative

News Headline: {headline}

"""
        
        if summary:
            prompt += f"Summary: {summary}\n\n"
        
        if link:
            prompt += f"Article Link: {link}\n\n"
        
        prompt += """
Format your response as:
1. [First tweet with summary and "Read more: {link}"]
2. [Second tweet with different angle and "Read more: {link}"]
3. [Third tweet with impact/analysis and "Read more: {link}"]

Make each tweet unique in approach:
- Tweet 1: Summarize the key facts
- Tweet 2: Focus on implications or impact
- Tweet 3: Ask a thought-provoking question or call-to-action

Include strategic hashtags and ensure each tweet tells a complete story.
"""
        
        return prompt
    
    def _parse_tweets_from_response(self, content: str) -> List[str]:
        """Parse tweets from OpenAI response."""
        tweets = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()            # Look for numbered lines
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
            
            # Generate hashtags based on headline content
            hashtags = self._generate_hashtags(clean_headline)
            hashtag_string = " ".join(hashtags)
            
            # Create more informative summary from headline
            summary_points = self._extract_key_points(clean_headline)
            
            tweets = []
            
            # Template 1: News summary format
            link_text = f"\n\nRead more: {link}" if link else ""
            
            # Create a more detailed first tweet
            if summary_points:
                tweet1 = f"🔥 {summary_points['main_point']}\n\n{summary_points['details']}\n\n{hashtag_string}{link_text}"
            else:
                tweet1 = f"🔥 Breaking: {clean_headline[:120]}...\n\nThis could impact how we think about technology and innovation.\n\n{hashtag_string}{link_text}"
            
            if len(tweet1) <= 280:
                tweets.append(tweet1)
            
            # Template 2: Impact/Analysis format
            impact_analysis = self._generate_impact_analysis(clean_headline)
            tweet2 = f"💡 Key insight: {impact_analysis}\n\n{clean_headline[:100]}...\n\n{hashtag_string}{link_text}"
            
            if len(tweet2) <= 280:
                tweets.append(tweet2)
            
            # Template 3: Question/Discussion format
            question = self._generate_discussion_question(clean_headline)
            tweet3 = f"🤔 {question}\n\n{clean_headline[:120]}...\n\nWhat's your take? 👇\n\n{hashtag_string}{link_text}"
            
            if len(tweet3) <= 280:
                tweets.append(tweet3)
            
            logger.info(f"Generated {len(tweets)} informative fallback tweets with summaries")
            return tweets
        
        except Exception as e:
            logger.error(f"Error generating fallback tweets: {e}")
            return []
    
    def _generate_fallback_tweets_with_summary(self, headline: str, summary: str, link: str) -> List[str]:
        """Generate tweets using template-based method with summary."""
        try:
            # Clean headline and summary
            clean_headline = headline.strip()
            clean_summary = summary.strip() if summary else ""
            
            # Generate hashtags based on headline content
            hashtags = self._generate_hashtags(clean_headline)
            hashtag_string = " ".join(hashtags)
            
            tweets = []
            link_text = f"\n\nRead more: {link}" if link else ""
              # Use summary for more informative tweets if available
            if clean_summary and len(clean_summary) > 20:
                # Template 1: Summary-based informative tweet
                summary_excerpt = clean_summary[:120] + "..." if len(clean_summary) > 120 else clean_summary
                tweet1 = f"📈 Breaking: {clean_headline[:50]}...\n\n{summary_excerpt}\n\n{hashtag_string}{link_text}"
                
                if len(tweet1) <= 280:
                    tweets.append(tweet1)
                
                # Template 2: Key takeaway format with more context
                key_points = clean_summary[:130] + "..." if len(clean_summary) > 130 else clean_summary
                tweet2 = f"💡 {key_points}\n\n{hashtag_string}{link_text}"
                
                if len(tweet2) <= 280:
                    tweets.append(tweet2)
                
                # Template 3: Discussion starter with context
                question = self._generate_discussion_question(clean_headline)
                context = clean_summary[:100] + "..." if len(clean_summary) > 100 else clean_summary
                tweet3 = f"🤔 {question}\n\n{context}\n\n{hashtag_string}{link_text}"
                
                if len(tweet3) <= 280:
                    tweets.append(tweet3)
            
            # If no good summary or tweets weren't generated, use original method
            if not tweets:
                return self._generate_fallback_tweets(headline, link)
            
            logger.info(f"Generated {len(tweets)} informative tweets using summary content")
            return tweets
        
        except Exception as e:
            logger.error(f"Error generating summary-based tweets: {e}")
            # Fallback to original method
            return self._generate_fallback_tweets(headline, link)

    def _generate_hashtags(self, headline: str) -> List[str]:
        """Generate relevant hashtags based on headline content."""
        hashtags = []
        headline_lower = headline.lower()
        
        # Technology related hashtags
        if any(word in headline_lower for word in ['ai', 'artificial intelligence', 'machine learning', 'ml']):
            hashtags.extend(['#AI', '#MachineLearning'])
        
        if any(word in headline_lower for word in ['crypto', 'bitcoin', 'blockchain', 'ethereum']):
            hashtags.extend(['#Crypto', '#Blockchain'])
        
        if any(word in headline_lower for word in ['tech', 'technology', 'innovation', 'startup']):
            hashtags.extend(['#Tech', '#Innovation'])
        
        if any(word in headline_lower for word in ['breaking', 'urgent', 'alert']):
            hashtags.append('#Breaking')
        
        if any(word in headline_lower for word in ['new', 'latest', 'update']):
            hashtags.append('#News')
        
        # Industry specific
        if any(word in headline_lower for word in ['google', 'microsoft', 'apple', 'meta', 'openai']):
            hashtags.append('#BigTech')
        
        if any(word in headline_lower for word in ['research', 'study', 'breakthrough']):
            hashtags.append('#Research')
        
        # Always include general hashtags if none specific found
        if not hashtags:
            hashtags = ['#Tech', '#News']
        
        # Limit to 3 hashtags to avoid spam
        return hashtags[:3]
    
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
    
    def _extract_key_points(self, headline: str) -> dict:
        """Extract key points from headline for summary."""
        headline_lower = headline.lower()
        
        # Try to identify main subject and action
        main_point = ""
        details = ""
        
        if "announces" in headline_lower or "launches" in headline_lower:
            main_point = "Major announcement in tech space"
            details = "New product/service could reshape the industry landscape."
        elif "breakthrough" in headline_lower or "discovers" in headline_lower:
            main_point = "Scientific breakthrough reported"
            details = "This discovery could lead to significant technological advances."
        elif "raises" in headline_lower and ("funding" in headline_lower or "million" in headline_lower):
            main_point = "Startup funding news"
            details = "Fresh capital injection signals investor confidence in this sector."
        elif "ai" in headline_lower or "artificial intelligence" in headline_lower:
            main_point = "AI development update"
            details = "Another step forward in artificial intelligence capabilities."
        elif "crypto" in headline_lower or "bitcoin" in headline_lower:
            main_point = "Cryptocurrency market movement"
            details = "Digital asset space continues to evolve with new developments."
        else:
            # Generic fallback
            words = headline.split()
            if len(words) > 6:
                main_point = " ".join(words[:6]) + "..."
                details = "Industry experts are watching this development closely."
            else:
                main_point = headline[:50] + "..."
                details = "This could have broader implications for the tech sector."
        
        return {
            "main_point": main_point,
            "details": details
        }
    
    def _generate_impact_analysis(self, headline: str) -> str:
        """Generate impact analysis based on headline content."""
        headline_lower = headline.lower()
        
        if "ai" in headline_lower:
            return "AI advances like this could transform how we work and interact with technology."
        elif "crypto" in headline_lower:
            return "Crypto developments often signal shifts in the broader financial landscape."
        elif "funding" in headline_lower:
            return "Venture funding rounds reveal where smart money sees future opportunities."
        elif "breakthrough" in headline_lower:
            return "Scientific breakthroughs today become tomorrow's game-changing products."
        elif "launch" in headline_lower:
            return "Product launches in tech often set trends for entire industries."
        elif "acquisition" in headline_lower or "merger" in headline_lower:
            return "M&A activity reshapes competitive landscapes and market dynamics."
        else:
            return "Developments like this often have ripple effects across the tech ecosystem."
    
    def _generate_discussion_question(self, headline: str) -> str:
        """Generate thought-provoking question based on headline."""
        headline_lower = headline.lower()
        
        if "ai" in headline_lower:
            return "How will AI developments like this change your daily workflow?"
        elif "privacy" in headline_lower or "data" in headline_lower:
            return "What does this mean for digital privacy and user rights?"
        elif "crypto" in headline_lower:
            return "Is this bullish or bearish for the crypto space long-term?"
        elif "startup" in headline_lower or "funding" in headline_lower:
            return "Which sector do you think will attract the most VC money next?"
        elif "regulation" in headline_lower:
            return "Will regulation help or hurt innovation in this space?"
        elif "breakthrough" in headline_lower:
            return "When do you think we'll see this technology in consumer products?"
        else:
            return "How do you think this will impact the industry?"
