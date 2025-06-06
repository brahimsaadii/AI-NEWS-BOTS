"""
Text generator using OpenAI API to create tweet suggestions from news headlines.
"""

import openai
import os
import logging
from typing import List, Optional, Dict, Any
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
                )            )
            
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
You are an expert analyst who deeply understands technology and business trends. Read this article content carefully and create 3 insightful tweets that show you truly comprehend the story's significance.

ARTICLE TO ANALYZE:
Headline: {headline}
"""
        
        if summary:
            prompt += f"\nFull Article Content: {summary}\n"
        
        prompt += f"""

INSTRUCTIONS:
Analyze the ENTIRE article content above. Don't just copy the first few sentences. Instead:

1. UNDERSTAND the core story, key players, context, and implications
2. IDENTIFY what makes this significant in the broader industry landscape  
3. EXTRACT unique insights that show deep understanding of the topic
4. CREATE commentary that demonstrates you've read and analyzed the full content

Generate 3 tweets (max 270 chars each) that show expert-level analysis:

TWEET 1: Key insight/implication 
- Analyze what this development really means
- Show understanding of broader context
- Include strategic implications or significance
- Use relevant emoji and 2-3 hashtags

TWEET 2: Industry perspective/trend analysis
- Connect this story to bigger industry trends
- Show how this fits into larger patterns
- Demonstrate expertise in the field
- Use relevant emoji and 2-3 hashtags

TWEET 3: Forward-looking analysis/discussion
- Predict implications or ask strategic questions
- Show understanding of future impact
- Engage audience with thoughtful perspective
- Use relevant emoji and 2-3 hashtags

Each tweet should read like it's from someone who:
- Actually read and understood the full article
- Has deep industry knowledge
- Can connect dots others might miss
- Provides genuine value and insight

DO NOT just copy the article's opening sentences. DO show real understanding and analysis.

Format as:
1. [Your analytical tweet about key insights]
2. [Your expert perspective on industry implications] 
3. [Your forward-looking analysis or strategic question]
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
            
            # Generate hashtags based on headline content
            hashtags = self._generate_hashtags(clean_headline)
            hashtag_string = " ".join(hashtags)
            
            # Create more informative summary from headline
            summary_points = self._extract_key_points(clean_headline)
            
            tweets = []
            
            # Template 1: Analysis/Implication format (no "Read more")
            if summary_points:
                tweet1 = f"🔥 {summary_points['main_point']}\n\n{summary_points['details']}\n\nThis could reshape how the industry approaches innovation.\n\n{hashtag_string}"
            else:
                tweet1 = f"🔥 Major development: {clean_headline[:100]}...\n\nThis signals a significant shift in the tech landscape.\n\n{hashtag_string}"
            
            # Add link only if there's space
            if len(tweet1) <= 250 and link:
                tweet1 += f"\n\n{link}"
            
            if len(tweet1) <= 280:
                tweets.append(tweet1)
            
            # Template 2: Insight/Context format
            impact_analysis = self._generate_impact_analysis(clean_headline)
            tweet2 = f"💡 {impact_analysis}\n\nKey takeaway from: {clean_headline[:80]}...\n\n{hashtag_string}"
              # Add link only if there's space
            if len(tweet2) <= 250 and link:
                tweet2 += f"\n\n{link}"
                
            if len(tweet2) <= 280:
                tweets.append(tweet2)
            
            # Template 3: Question/Discussion format
            question = self._generate_discussion_question(clean_headline)
            tweet3 = f"🤔 {question}\n\nTriggered by: {clean_headline[:70]}...\n\nWhat's your take? 👇\n\n{hashtag_string}"
            
            # Add link only if there's space
            if len(tweet3) <= 250 and link:
                tweet3 += f"\n\n{link}"
            
            if len(tweet3) <= 280:
                tweets.append(tweet3)
            
            logger.info(f"Generated {len(tweets)} discussion-focused fallback tweets")
            return tweets
        
        except Exception as e:
            logger.error(f"Error generating fallback tweets: {e}")
            return []
    
    def _generate_fallback_tweets_with_summary(self, headline: str, summary: str, link: str) -> List[str]:
        """Generate tweets using intelligent content analysis."""
        try:
            # Clean headline and summary
            clean_headline = headline.strip()
            clean_summary = summary.strip() if summary else ""
            
            # Generate hashtags based on headline content
            hashtags = self._generate_hashtags(clean_headline)
            hashtag_string = " ".join(hashtags)
            
            tweets = []
            
            # Use intelligent content analysis if we have a summary
            if clean_summary and len(clean_summary) > 50:
                analysis = self._analyze_article_content(clean_headline, clean_summary)
                
                # Template 1: Industry Impact Analysis
                if analysis.get('impact'):
                    tweet1 = f"🎯 Industry Impact Alert:\n\n{analysis['impact']}\n\nThis shift in {analysis.get('sector', 'tech')} could redefine competitive landscapes.\n\n{hashtag_string}"
                    if len(tweet1) <= 250 and link:
                        tweet1 += f"\n\n{link}"
                    if len(tweet1) <= 280:
                        tweets.append(tweet1)
                
                # Template 2: Strategic Insights
                if analysis.get('insight'):
                    tweet2 = f"💡 Strategic Perspective:\n\n{analysis['insight']}\n\nThe timing suggests this is more than just market positioning.\n\n{hashtag_string}"
                    if len(tweet2) <= 250 and link:
                        tweet2 += f"\n\n{link}"
                    if len(tweet2) <= 280:
                        tweets.append(tweet2)
                
                # Template 3: Future Implications
                if analysis.get('future_question'):
                    tweet3 = f"🔮 Looking Ahead:\n\n{analysis['future_question']}\n\nThis development opens fascinating questions about where the industry is heading.\n\n{hashtag_string}"
                    if len(tweet3) <= 250 and link:
                        tweet3 += f"\n\n{link}"
                    if len(tweet3) <= 280:
                        tweets.append(tweet3)
            
            # If no good analysis or tweets weren't generated, use enhanced fallback
            if not tweets:
                return self._generate_fallback_tweets(headline, link)
            
            logger.info(f"Generated {len(tweets)} analytically-driven tweets from content analysis")
            return tweets
        
        except Exception as e:
            logger.error(f"Error generating analysis-based tweets: {e}")
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

    async def generate_tweet(self, content_context: dict) -> Optional[str]:
        """Generate a single tweet from various content types."""
        try:
            content_type = content_context.get('type', 'news')
            
            if content_type == 'newsletter':
                return await self._generate_newsletter_tweet(content_context)
            else:
                # Default to news tweet generation
                headline = content_context.get('title', '')
                summary = content_context.get('summary', '')
                link = content_context.get('link', '')
                
                tweets = await self.generate_tweets(headline, summary, link)
                return tweets[0] if tweets else None
                
        except Exception as e:
            logger.error(f"Error generating tweet: {e}")
            return None
    
    async def _generate_newsletter_tweet(self, context: dict) -> Optional[str]:
        """Generate tweet specifically from newsletter content."""
        try:
            subject = context.get('subject', '')
            sender = context.get('sender', '')
            articles = context.get('articles', [])
            summary = context.get('summary', '')
            categories = context.get('categories', [])
            niche = context.get('niche', 'general')
            
            # Try OpenAI first if available
            if self.api_key:
                tweet = await self._generate_newsletter_with_openai(context)
                if tweet:
                    return tweet
            
            # Fallback to template-based generation
            return self._generate_newsletter_fallback(context)
            
        except Exception as e:
            logger.error(f"Error generating newsletter tweet: {e}")
            return None
    
    async def _generate_newsletter_with_openai(self, context: dict) -> Optional[str]:
        """Generate newsletter tweet using OpenAI."""
        try:
            prompt = self._create_newsletter_prompt(context)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a social media expert who creates engaging tweets from newsletter content."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.7
                )
            )
            
            tweet = response.choices[0].message.content.strip()
            
            # Clean up the tweet
            if tweet.startswith('"') and tweet.endswith('"'):
                tweet = tweet[1:-1]
            
            return tweet if len(tweet) <= 280 else tweet[:277] + "..."
            
        except Exception as e:
            logger.error(f"Error with OpenAI newsletter generation: {e}")
            return None
    
    def _create_newsletter_prompt(self, context: dict) -> str:
        """Create prompt for newsletter tweet generation."""
        subject = context.get('subject', '')
        sender = context.get('sender', '')
        articles = context.get('articles', [])
        summary = context.get('summary', '')
        categories = context.get('categories', [])
        niche = context.get('niche', 'general')
        
        # Build article list
        article_text = ""
        for i, article in enumerate(articles[:3], 1):
            article_text += f"{i}. {article.get('title', '')}\n"
        
        # Build categories text
        categories_text = ", ".join(categories) if categories else "technology"
        
        prompt = f"""Create a single engaging tweet about this newsletter content:

Newsletter Subject: {subject}
From: {sender}
Categories: {categories_text}
Target Niche: {niche}

Key Articles:
{article_text}

Summary: {summary}

Requirements:
- Single tweet (max 280 characters)
- Engaging and informative
- Include relevant hashtags for {niche}
- Mention key insights or trends
- Professional but conversational tone
- Focus on value to readers

Generate one tweet only:"""
        
        return prompt
    
    def _generate_newsletter_fallback(self, context: dict) -> str:
        """Generate newsletter tweet using templates."""
        try:
            subject = context.get('subject', '')
            articles = context.get('articles', [])
            categories = context.get('categories', [])
            niche = context.get('niche', 'general')
            
            # Get hashtags based on niche and categories
            hashtags = self._get_niche_hashtags(niche, categories)
            
            # Choose template based on content
            if articles:
                # Article-focused template
                top_article = articles[0].get('title', '')
                if len(top_article) > 60:
                    top_article = top_article[:60] + "..."
                
                tweet = f"📧 Newsletter highlights: {top_article}"
                
                if len(articles) > 1:
                    tweet += f" + {len(articles)-1} more insights"
                
                tweet += f"\n\n{' '.join(hashtags[:3])}"
            
            elif subject:
                # Subject-focused template
                clean_subject = subject.replace('Re:', '').replace('Fwd:', '').strip()
                if len(clean_subject) > 100:
                    clean_subject = clean_subject[:100] + "..."
                
                tweet = f"📰 Weekly roundup: {clean_subject}\n\n{' '.join(hashtags[:3])}"
            
            else:
                # Generic template
                tweet = f"📧 Interesting newsletter insights in {niche}\n\n{' '.join(hashtags[:3])}"
            
            return tweet if len(tweet) <= 280 else tweet[:277] + "..."
            
        except Exception as e:
            logger.error(f"Error in newsletter fallback generation: {e}")
            return f"📧 Newsletter update in {context.get('niche', 'tech')} #{context.get('niche', 'tech').replace(' ', '')}"
    
    def _get_niche_hashtags(self, niche: str, categories: List[str]) -> List[str]:
        """Get relevant hashtags for niche and categories."""
        hashtag_map = {
            'tech': ['#TechNews', '#Innovation', '#Technology'],
            'ai': ['#AI', '#MachineLearning', '#ArtificialIntelligence'],
            'crypto': ['#Crypto', '#Bitcoin', '#Blockchain'],
            'business': ['#Business', '#Startup', '#Entrepreneurship'],
            'general': ['#News', '#Update', '#Trending']
        }
        
        # Get base hashtags for niche
        base_hashtags = hashtag_map.get(niche.lower(), hashtag_map['general'])
        
        # Add category-specific hashtags
        category_hashtags = []
        for category in categories:
            if category.lower() in hashtag_map:
                category_hashtags.extend(hashtag_map[category.lower()][:1])
        
        # Combine and deduplicate
        all_hashtags = base_hashtags + category_hashtags
        return list(dict.fromkeys(all_hashtags))  # Remove duplicates while preserving order
    
    async def generate_job_tweet(self, job_content: Dict[str, Any]) -> Optional[str]:
        """Generate tweet from job posting content."""
        try:
            title = job_content.get('title', '')
            company = job_content.get('company', '')
            location = job_content.get('location', '')
            url = job_content.get('url', '')
            search_query = job_content.get('search_query', '')
            
            if not title or not company:
                return None
            
            # Try OpenAI first if available
            if self.api_key:
                openai_tweet = await self._generate_job_tweet_with_openai(job_content)
                if openai_tweet:
                    return openai_tweet
            
            # Fallback to template-based generation
            return self._generate_job_tweet_fallback(job_content)
            
        except Exception as e:
            logger.error(f"Error generating job tweet: {e}")
            return None
    
    async def _generate_job_tweet_with_openai(self, job_content: Dict[str, Any]) -> Optional[str]:
        """Generate job tweet using OpenAI API."""
        try:
            title = job_content.get('title', '')
            company = job_content.get('company', '')
            location = job_content.get('location', '')
            content = job_content.get('content', '')
            search_query = job_content.get('search_query', '')
            url = job_content.get('url', '')
            
            prompt = f"""Create an engaging tweet for a job posting. Make it professional but attention-grabbing.

Job Details:
- Title: {title}
- Company: {company}
- Location: {location}
- Search Query: {search_query}
- Description: {content[:200]}

Requirements:
- Under 280 characters
- Include relevant hashtags
- Professional tone
- Mention the role and company
- Add location if significant
- Include URL if provided: {url}

Generate just the tweet text, no explanations."""

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a professional recruiter who creates engaging job posting tweets."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.7
                )
            )
            
            tweet = response.choices[0].message.content.strip()
            
            # Ensure it's under 280 characters
            if len(tweet) > 280:
                tweet = tweet[:277] + "..."
            
            logger.info("Successfully generated job tweet with OpenAI")
            return tweet
            
        except Exception as e:
            logger.error(f"Error generating job tweet with OpenAI: {e}")
            return None
    
    def _generate_job_tweet_fallback(self, job_content: Dict[str, Any]) -> str:
        """Generate job tweet using template-based approach."""
        try:
            title = job_content.get('title', 'Position')
            company = job_content.get('company', 'Company')
            location = job_content.get('location', '')
            search_query = job_content.get('search_query', '')
            url = job_content.get('url', '')
            
            # Generate hashtags based on job title and search query
            hashtags = self._get_job_hashtags(title, search_query)
            
            # Build tweet variants
            templates = [
                f"💼 {title} at {company}",
                f"🚀 New opportunity: {title}",
                f"💡 {company} is hiring: {title}",
                f"🎯 Job alert: {title} at {company}",
                f"📢 Now hiring: {title}"
            ]
            
            # Choose template based on length
            base_tweet = ""
            for template in templates:
                base_length = len(template)
                if location:
                    base_length += len(f" - {location}")
                if hashtags:
                    base_length += len(f" {' '.join(hashtags[:2])}")
                if url:
                    base_length += 25  # Shortened URL length
                
                if base_length <= 260:  # Leave some buffer
                    base_tweet = template
                    break
            
            if not base_tweet:
                base_tweet = templates[0]  # Use first template as fallback
            
            # Add location if it fits
            if location and len(base_tweet + f" - {location}") <= 240:
                base_tweet += f" - {location}"
            
            # Add hashtags
            if hashtags:
                hashtag_text = f" {' '.join(hashtags[:2])}"
                if len(base_tweet + hashtag_text) <= 260:
                    base_tweet += hashtag_text
            
            # Add URL if it fits
            if url and len(base_tweet) <= 255:
                base_tweet += f" {url}"
            
            return base_tweet if len(base_tweet) <= 280 else base_tweet[:277] + "..."
            
        except Exception as e:
            logger.error(f"Error in job tweet fallback generation: {e}")
            return f"💼 New job opportunity at {job_content.get('company', 'a great company')} #Jobs #Hiring"
    
    def _get_job_hashtags(self, title: str, search_query: str) -> List[str]:
        """Get relevant hashtags for job posting."""
        hashtags = ['#Jobs', '#Hiring']
        
        # Job category hashtags based on common keywords
        job_keywords = {
            'developer': ['#Developer', '#Programming'],
            'engineer': ['#Engineering', '#Tech'],
            'software': ['#SoftwareJobs', '#Tech'],
            'data': ['#DataJobs', '#Analytics'],
            'manager': ['#Management', '#Leadership'],
            'designer': ['#Design', '#Creative'],
            'marketing': ['#Marketing', '#Digital'],
            'sales': ['#Sales', '#Business'],
            'analyst': ['#Analytics', '#Business'],
            'consultant': ['#Consulting', '#Business'],
            'remote': ['#RemoteWork', '#Remote'],
            'senior': ['#Senior', '#Experienced'],
            'junior': ['#Junior', '#EntryLevel'],
            'internship': ['#Internship', '#Students']
        }
        
        # Check title and search query for keywords
        text_to_check = f"{title} {search_query}".lower()
        
        for keyword, tags in job_keywords.items():
            if keyword in text_to_check:
                hashtags.extend(tags[:1])  # Add first tag for each match
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(hashtags))
    
    def _analyze_article_content(self, headline: str, summary: str) -> dict:
        """Analyze article content to extract genuine insights and implications."""
        try:
            headline_lower = headline.lower()
            summary_lower = summary.lower()
            combined_text = f"{headline} {summary}".lower()
            
            analysis = {}
            
            # Extract industry impact
            if any(word in combined_text for word in ['ai', 'artificial intelligence', 'machine learning']):
                if 'breakthrough' in combined_text or 'advance' in combined_text:
                    analysis['impact'] = "AI capabilities are advancing faster than regulatory frameworks can adapt."
                elif 'partnership' in combined_text or 'collaboration' in combined_text:
                    analysis['impact'] = "Strategic AI partnerships signal a shift toward ecosystem-based innovation."
                elif 'investment' in combined_text or 'funding' in combined_text:
                    analysis['impact'] = "AI investment patterns reveal where the market sees transformative potential."
                else:
                    analysis['impact'] = "AI developments like this reshape competitive advantages across industries."
                analysis['sector'] = 'AI'
                
            elif any(word in combined_text for word in ['crypto', 'blockchain', 'bitcoin', 'ethereum']):
                if 'regulation' in combined_text:
                    analysis['impact'] = "Crypto regulation creates clarity but may also limit innovation vectors."
                elif 'adoption' in combined_text or 'mainstream' in combined_text:
                    analysis['impact'] = "Mainstream crypto adoption signals institutional confidence in digital assets."
                else:
                    analysis['impact'] = "Blockchain innovations continue pushing the boundaries of decentralized systems."
                analysis['sector'] = 'crypto'
                
            elif any(word in combined_text for word in ['startup', 'funding', 'investment', 'venture']):
                if 'series' in combined_text or 'round' in combined_text:
                    analysis['impact'] = "Venture funding flows reveal investor conviction in emerging market segments."
                else:
                    analysis['impact'] = "Startup ecosystem dynamics show where innovation capital is concentrating."
                analysis['sector'] = 'venture capital'
                
            elif any(word in combined_text for word in ['google', 'microsoft', 'apple', 'meta', 'amazon']):
                analysis['impact'] = "Big Tech moves create ripple effects throughout the entire technology ecosystem."
                analysis['sector'] = 'big tech'
                
            else:
                # Generic tech analysis
                analysis['impact'] = "Technology shifts like this often have broader implications than initially apparent."
                analysis['sector'] = 'technology'
            
            # Extract strategic insights
            if 'partnership' in combined_text or 'collaboration' in combined_text:
                analysis['insight'] = "Strategic alliances often signal market convergence points that single players can't capture alone."
            elif 'acquisition' in combined_text or 'merger' in combined_text:
                analysis['insight'] = "M&A activity reveals which capabilities companies view as existential for future competitiveness."
            elif 'launch' in combined_text or 'release' in combined_text:
                analysis['insight'] = "Product timing suggests this addresses a market gap that competitors haven't yet filled."
            elif 'research' in combined_text or 'study' in combined_text:
                analysis['insight'] = "Research findings today become tomorrow's competitive advantages for early adopters."
            elif 'regulation' in combined_text or 'policy' in combined_text:
                analysis['insight'] = "Regulatory developments reshape the playing field, often favoring established players over disruptors."
            else:
                analysis['insight'] = "Market movements like this often reflect deeper shifts in consumer behavior and enterprise needs."
            
            # Generate forward-looking questions
            if analysis['sector'] == 'AI':
                analysis['future_question'] = "Will this AI advancement democratize capabilities or concentrate them further among tech giants?"
            elif analysis['sector'] == 'crypto':
                analysis['future_question'] = "How will traditional financial institutions respond to this crypto development?"
            elif analysis['sector'] == 'venture capital':
                analysis['future_question'] = "What does this funding pattern tell us about which technologies will dominate in 2-3 years?"
            else:
                analysis['future_question'] = "What second-order effects might this development trigger across adjacent industries?"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing article content: {e}")
            return {
                'impact': "This development signals significant changes in the technology landscape.",
                'insight': "Market dynamics suggest this is more than just another product announcement.",
                'future_question': "How will this reshape competitive dynamics in the coming months?",
                'sector': 'technology'
            }
