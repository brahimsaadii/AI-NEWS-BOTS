#!/usr/bin/env python3
"""
Test script to verify all components are working correctly.
"""

import sys
import os
import asyncio
import logging

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from botfather.config_manager import ConfigManager
        print("✅ ConfigManager imported successfully")
    except ImportError as e:
        print(f"❌ ConfigManager import failed: {e}")
        return False
    
    try:
        from sources.rss_fetcher import RSSFetcher
        print("✅ RSSFetcher imported successfully")
    except ImportError as e:
        print(f"❌ RSSFetcher import failed: {e}")
        return False
    
    try:
        from utils.text_generator import TextGenerator
        print("✅ TextGenerator imported successfully")
    except ImportError as e:
        print(f"❌ TextGenerator import failed: {e}")
        return False
    
    try:
        from utils.x_poster import XPoster
        print("✅ XPoster imported successfully")
    except ImportError as e:
        print(f"❌ XPoster import failed: {e}")
        return False
    
    return True

def test_config_manager():
    """Test ConfigManager functionality."""
    print("\n🔧 Testing ConfigManager...")
    
    try:
        from botfather.config_manager import ConfigManager
    
    try:
        config_manager = ConfigManager()
        
        # Test adding a bot
        test_config = {
            'name': 'Test Bot',
            'token': 'test_token',
            'niche': 'tech',
            'frequency': 6,
            'auto_post': False,
            'owner_id': 12345
        }
        
        bot_id = config_manager.add_bot(test_config)
        print(f"✅ Bot added with ID: {bot_id}")
        
        # Test retrieving bot
        retrieved_config = config_manager.get_bot(bot_id)
        if retrieved_config:
            print("✅ Bot configuration retrieved successfully")
        else:
            print("❌ Failed to retrieve bot configuration")
            return False
        
        # Test deleting bot
        if config_manager.delete_bot(bot_id):
            print("✅ Bot deleted successfully")
        else:
            print("❌ Failed to delete bot")
            return False
        
        return True
    
    except Exception as e:
        print(f"❌ ConfigManager test failed: {e}")
        return False

async def test_rss_fetcher():
    """Test RSS fetcher functionality."""
    print("\n📡 Testing RSS Fetcher...")
    
    try:
        fetcher = RSSFetcher('tech')
        
        # Test source configuration
        sources = fetcher.sources
        print(f"✅ Configured {len(sources)} RSS sources for tech niche")
        
        # Test fetching (with a small timeout)
        print("🔄 Testing news fetch (this may take a moment)...")
        articles = await fetcher.fetch_latest_articles(hours_back=48)
        
        if articles:
            print(f"✅ Successfully fetched {len(articles)} articles")
            print(f"   Sample headline: {articles[0].get('title', 'N/A')[:80]}...")
        else:
            print("⚠️ No articles fetched (this might be normal)")
        
        return True
    
    except Exception as e:
        print(f"❌ RSS Fetcher test failed: {e}")
        return False

def test_text_generator():
    """Test text generator functionality."""
    print("\n✍️ Testing Text Generator...")
    
    try:
        generator = TextGenerator()
        
        # Test fallback tweet generation (doesn't require API key)
        test_headline = "OpenAI Releases New AI Model That Can Code"
        tweets = generator._generate_fallback_tweets(test_headline, "https://example.com")
        
        if tweets:
            print(f"✅ Generated {len(tweets)} fallback tweets")
            print(f"   Sample tweet: {tweets[0][:60]}...")
        else:
            print("❌ Failed to generate fallback tweets")
            return False
        
        # Test API connection (will show warning if no API key)
        api_working = generator.test_api_connection()
        if api_working:
            print("✅ OpenAI API connection successful")
        else:
            print("⚠️ OpenAI API not configured (will use fallback tweets)")
        
        return True
    
    except Exception as e:
        print(f"❌ Text Generator test failed: {e}")
        return False

def test_x_poster():
    """Test X poster functionality."""
    print("\n🐦 Testing X Poster...")
    
    try:
        poster = XPoster()
        
        # Test API connection (will show warning if no token)
        api_working = poster.test_api_connection()
        if api_working:
            print("✅ X API connection successful")
        else:
            print("⚠️ X API not configured (will simulate posting)")
        
        return True
    
    except Exception as e:
        print(f"❌ X Poster test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 News Tweet Bots - System Test\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Config Manager Test", test_config_manager),
        ("RSS Fetcher Test", test_rss_fetcher),
        ("Text Generator Test", test_text_generator),
        ("X Poster Test", test_x_poster)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
    
    print(f"\n{'='*50}")
    print(f"TEST SUMMARY: {passed}/{total} tests passed")
    print('='*50)
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and add your API keys")
        print("2. Get a Telegram bot token from @BotFather")
        print("3. Run: python main.py")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise
    asyncio.run(main())
