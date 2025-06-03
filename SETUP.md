# 🚀 Quick Setup Guide

## Prerequisites
- Python 3.8+ installed
- Telegram account
- (Optional) OpenAI API key for AI tweet generation
- (Optional) X (Twitter) API access for posting tweets

## Step 1: Create Your Main Telegram Bot

1. Open Telegram and go to [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Choose a name for your main controller bot (e.g., "My News Bot Manager")
4. Choose a username (e.g., "mynewsbotmanager_bot")
5. **Save the token** you receive - you'll need it to start the system

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Or run the package check:
```bash
python check_install.py
```

## Step 3: Configure API Keys (Optional but Recommended)

1. Copy `.env.example` to `.env`
2. Edit `.env` and add your API keys:

```env
# For AI tweet generation (get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=your_openai_api_key_here

# For posting to X/Twitter (get from https://developer.twitter.com/)
X_BEARER_TOKEN=your_x_bearer_token_here
```

> **Note:** The system works without these keys but will have limited functionality:
> - Without OpenAI: Uses simple template-based tweet generation
> - Without X API: Simulates posting (shows what would be posted)

## Step 4: Start the System

### Option A: Command Line
```bash
python main.py
```

### Option B: Using Batch File (Windows)
```cmd
start.bat
```

### Option C: Using PowerShell Script
```powershell
.\start.ps1
```

## Step 5: Create Your First News Bot

1. Start the system and enter your BotFather token
2. Go to Telegram and find your main bot
3. Send `/start` to your bot
4. Send `/addbot` and follow the interactive setup:
   - **Bot Name**: "Tech News Bot"
   - **Bot Token**: Create another bot with @BotFather for this specific niche
   - **Niche**: Choose from Tech, Crypto, AI, General, or Custom
   - **Frequency**: How often to check for news (1-24 hours)
   - **Sources**: Use default RSS feeds or add custom ones
   - **Posting**: Manual approval or auto-posting

## Step 6: Start Your News Bot

1. Send `/listbots` to see your created bots
2. Send `/startbot` and select the bot to activate
3. Your bot will start fetching news and sending tweet suggestions!

## 🎯 Usage Commands

### BotFather Commands (Main Controller Bot)
- `/start` - Welcome and overview
- `/addbot` - Create a new news bot
- `/listbots` - Show all your bots
- `/startbot` - Start a stopped bot
- `/stopbot` - Stop a running bot  
- `/deletebot` - Delete a bot permanently
- `/help` - Show help

### Individual News Bot Commands
- `/start` - Bot introduction
- `/status` - Check bot status and stats
- `/latest` - Manually fetch latest news

## 🔧 Troubleshooting

### Common Issues

**"Bot not responding"**
- Check your Telegram bot token is correct
- Make sure the bot is not already running elsewhere

**"No tweets generated"**  
- Check your OpenAI API key in `.env`
- The system will fall back to template tweets if OpenAI is not configured

**"Cannot post to X"**
- Check your X Bearer Token in `.env`
- Posting will be simulated if X API is not configured

**"No news articles found"**
- RSS feeds might be temporarily unavailable
- Try a different niche or add custom RSS feeds

### Logs and Debugging

The system prints detailed logs to the console. Look for:
- ✅ Success messages
- ⚠️ Warnings (usually non-critical)
- ❌ Errors (need attention)

### Testing the System

Run the comprehensive test:
```bash
python test_system.py
```

This will verify all components are working correctly.

## 🌟 Tips for Best Results

1. **Start Simple**: Begin with one bot for a niche you're interested in
2. **Test First**: Use manual approval initially to see what tweets are generated
3. **Customize Sources**: Add RSS feeds specific to your interests
4. **Monitor Performance**: Check logs regularly for any issues
5. **Gradual Automation**: Once comfortable, enable auto-posting

## 📱 Example Workflow

1. Tech News Bot finds: "Apple Announces New MacBook Pro"
2. AI generates tweet suggestions:
   - "🍎 Apple just dropped the new MacBook Pro and it's a game-changer! Here's what you need to know 👇"
   - "The new MacBook Pro is here. Faster, smarter, more powerful. Welcome to the future of laptops."
   - "Apple's latest MacBook Pro just raised the bar. Again. 💻✨"
3. You receive these in Telegram with buttons to choose which one to post
4. Selected tweet gets posted to your X account

## 🆘 Need Help?

1. Check this guide first
2. Run `python test_system.py` to diagnose issues
3. Check the console logs for error messages
4. Review the README.md for detailed information

---

**Happy tweeting! 🐦**
