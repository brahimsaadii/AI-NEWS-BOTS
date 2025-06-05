"""
X (Twitter) poster utility for posting tweets using X API.
"""

import os
import requests
import logging
from typing import Optional, Dict, Any
from requests_oauthlib import OAuth1

logger = logging.getLogger(__name__)

class XPoster:
    """Posts tweets to X (Twitter) using the X API."""
    
    def __init__(self, bearer_token: Optional[str] = None, api_key: Optional[str] = None, 
                 api_secret: Optional[str] = None, access_token: Optional[str] = None, 
                 access_token_secret: Optional[str] = None):
        """Initialize X poster with API credentials.
        
        Args:
            bearer_token: X Bearer Token for API v2
            api_key: X API Key 
            api_secret: X API Secret
            access_token: X Access Token
            access_token_secret: X Access Token Secret
        """
        # Use provided credentials or fall back to environment variables
        self.bearer_token = bearer_token or os.getenv('X_BEARER_TOKEN')
        self.api_key = api_key or os.getenv('X_API_KEY')
        self.api_secret = api_secret or os.getenv('X_API_SECRET')
        self.access_token = access_token or os.getenv('X_ACCESS_TOKEN')
        self.access_token_secret = access_token_secret or os.getenv('X_ACCESS_TOKEN_SECRET')
        
        self.api_base = "https://api.twitter.com/2"
        
        # Check if we have any credentials
        has_bearer = bool(self.bearer_token)
        has_oauth = bool(self.api_key and self.api_secret and self.access_token and self.access_token_secret)
        
        if not has_bearer and not has_oauth:
            logger.warning("No X credentials provided. Tweet posting will be simulated.")
        elif has_bearer:
            logger.info("X Bearer Token found - using API v2")
        elif has_oauth:
            logger.info("X OAuth credentials found - using API v2 with OAuth")
    
    async def post_tweet(self, text: str) -> bool:
        """Post a tweet to X (Twitter)."""
        if not text or len(text) > 280:
            logger.error(f"Invalid tweet text length: {len(text)}")
            return False
        
        # Debug logging
        logger.info(f"XPoster attempting to post tweet...")
        logger.info(f"Bearer token available: {bool(self.bearer_token)}")
        logger.info(f"OAuth credentials available: {bool(self.api_key and self.api_secret and self.access_token and self.access_token_secret)}")
        
        # Check if we have any credentials
        if not self.bearer_token and not (self.api_key and self.api_secret and self.access_token and self.access_token_secret):
            # Simulate posting
            logger.info(f"SIMULATED TWEET POST: {text}")
            return True
        
        try:
            # Prepare tweet data
            tweet_data = {
                "text": text
            }
            
            # Make API request based on available credentials
            if self.bearer_token:
                logger.info("Using Bearer Token authentication")
                headers = {
                    "Authorization": f"Bearer {self.bearer_token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    f"{self.api_base}/tweets",
                    json=tweet_data,
                    headers=headers,
                    timeout=10
                )
            else:
                # Use OAuth 1.0a authentication
                logger.info("Using OAuth 1.0a authentication")
                auth = OAuth1(
                    self.api_key,
                    client_secret=self.api_secret,
                    resource_owner_key=self.access_token,
                    resource_owner_secret=self.access_token_secret,
                    signature_type='AUTH_HEADER'
                )
                
                response = requests.post(
                    f"{self.api_base}/tweets",
                    json=tweet_data,
                    auth=auth,
                    headers={"Content-Type": "application/json"},
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
    
    def set_credentials(self, bearer_token: str = None, api_key: str = None, 
                       api_secret: str = None, access_token: str = None, 
                       access_token_secret: str = None):
        """Set X API credentials."""
        if bearer_token:
            self.bearer_token = bearer_token
        if api_key:
            self.api_key = api_key
        if api_secret:
            self.api_secret = api_secret
        if access_token:
            self.access_token = access_token
        if access_token_secret:
            self.access_token_secret = access_token_secret
    
    def test_api_connection(self) -> bool:
        """Test if X API connection is working."""
        if not self.bearer_token and not (self.api_key and self.api_secret and self.access_token and self.access_token_secret):
            return False
        
        try:
            if self.bearer_token:
                # Test with a simple API call (get user info)
                response = requests.get(
                    f"{self.api_base}/users/me",
                    headers={
                        "Authorization": f"Bearer {self.bearer_token}"
                    },
                    timeout=10
                )
            else:
                # Test with OAuth
                auth = OAuth1(
                    self.api_key,
                    client_secret=self.api_secret,
                    resource_owner_key=self.access_token,
                    resource_owner_secret=self.access_token_secret,
                    signature_type='AUTH_HEADER'
                )
                
                response = requests.get(
                    f"{self.api_base}/users/me",
                    auth=auth,
                    timeout=10
                )
            
            return response.status_code == 200
        
        except Exception as e:
            logger.error(f"X API test failed: {e}")
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        if not self.bearer_token and not (self.api_key and self.api_secret and self.access_token and self.access_token_secret):
            return {"error": "No credentials provided"}
        
        try:
            if self.bearer_token:
                response = requests.get(
                    f"{self.api_base}/tweets",
                    headers={
                        "Authorization": f"Bearer {self.bearer_token}"
                    },
                    timeout=10
                )
            else:
                auth = OAuth1(
                    self.api_key,
                    client_secret=self.api_secret,
                    resource_owner_key=self.access_token,
                    resource_owner_secret=self.access_token_secret,
                    signature_type='AUTH_HEADER'
                )
                
                response = requests.get(
                    f"{self.api_base}/tweets",
                    auth=auth,
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
