"""
X (Twitter) poster utility for posting tweets using X API.
"""

import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class XPoster:
    """Posts tweets to X (Twitter) using the X API."""
    
    def __init__(self, bearer_token: Optional[str] = None):
        """Initialize X poster with bearer token."""
        self.bearer_token = bearer_token or os.getenv('X_BEARER_TOKEN')
        self.api_base = "https://api.twitter.com/2"
        
        if not self.bearer_token:
            logger.warning("X Bearer Token not provided. Tweet posting will be simulated.")
    
    async def post_tweet(self, text: str) -> bool:
        """Post a tweet to X (Twitter)."""
        if not text or len(text) > 280:
            logger.error(f"Invalid tweet text length: {len(text)}")
            return False
        
        if not self.bearer_token:
            # Simulate posting
            logger.info(f"SIMULATED TWEET POST: {text}")
            return True
        
        try:
            # Prepare tweet data
            tweet_data = {
                "text": text
            }
            
            # Make API request
            response = requests.post(
                f"{self.api_base}/tweets",
                json=tweet_data,
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 201:
                tweet_info = response.json()
                tweet_id = tweet_info.get('data', {}).get('id')
                logger.info(f"Successfully posted tweet (ID: {tweet_id}): {text}")
                return True
            else:
                logger.error(f"Failed to post tweet. Status: {response.status_code}, Response: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return False
    
    async def post_tweet_with_media(self, text: str, media_urls: list = None) -> bool:
        """Post a tweet with media attachments."""
        # For now, just post text
        # Media upload would require additional implementation
        return await self.post_tweet(text)
    
    def set_bearer_token(self, bearer_token: str):
        """Set X API bearer token."""
        self.bearer_token = bearer_token
    
    def test_api_connection(self) -> bool:
        """Test if X API connection is working."""
        if not self.bearer_token:
            return False
        
        try:
            # Test with a simple API call (get user info)
            response = requests.get(
                f"{self.api_base}/users/me",
                headers={
                    "Authorization": f"Bearer {self.bearer_token}"
                },
                timeout=10
            )
            
            return response.status_code == 200
        
        except Exception as e:
            logger.error(f"X API test failed: {e}")
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        if not self.bearer_token:
            return {"error": "No bearer token provided"}
        
        try:
            response = requests.get(
                f"{self.api_base}/tweets",
                headers={
                    "Authorization": f"Bearer {self.bearer_token}"
                },
                timeout=10
            )
            
            # Extract rate limit headers
            rate_limit_info = {
                "limit": response.headers.get("x-rate-limit-limit"),
                "remaining": response.headers.get("x-rate-limit-remaining"),
                "reset": response.headers.get("x-rate-limit-reset")
            }
            
            return rate_limit_info
        
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {"error": str(e)}
