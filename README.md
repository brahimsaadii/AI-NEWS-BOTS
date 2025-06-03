# News Tweet Bots

A Telegram bot system that creates and manages multiple news bots for different niches. Each bot fetches news from RSS feeds and generates tweet suggestions using AI.

## 🚀 Features

- **BotFather Controller**: Central bot to create and manage multiple news bots
- **Multiple Niches**: Support for Tech, Crypto, AI, and General news categories
- **AI Tweet Generation**: Uses OpenAI API to create engaging tweet suggestions
- **Manual/Auto Posting**: Choose between manual approval or automatic posting to X (Twitter)
- **RSS Feed Support**: Fetches news from multiple RSS sources
- **Configurable Frequency**: Set update intervals (1-24 hours)
- **Custom Sources**: Add your own RSS feeds

## 📁 Project Structure

```
news-tweet-bots/
├── botfather/                  # Controller bot
│   ├── botfather.py           # Main BotFather logic
│   ├── config_manager.py      # Configuration management
│   └── bot_registry.yaml      # Bot configurations storage
├── bots/                      # Individual bot runner
│   └── news_bot.py           # News bot implementation
├── sources/                   # News source fetchers
│   └── rss_fetcher.py        # RSS feed parser
├── utils/                     # Utilities
│   ├── x_poster.py           # X (Twitter) API integration
│   └── text_generator.py     # OpenAI integration
├── main.py                    # Entry point
└── requirements.txt           # Dependencies
```

## 🛠️ Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file with your API keys:

```env
# OpenAI API Key (for tweet generation)
OPENAI_API_KEY=your_openai_api_key_here

# X (Twitter) Bearer Token (for posting tweets)
X_BEARER_TOKEN=your_x_bearer_token_here
```

### 3. Create Telegram Bots

1. Go to [@BotFather](https://t.me/BotFather) on Telegram
2. Create a main controller bot using `/newbot`
3. Save the token for the BotFather
4. Create additional bots for each news niche you want

### 4. Run the System

```bash
python main.py
```

Enter your BotFather token when prompted.

## 📱 Usage

### BotFather Commands

- `/start` - Welcome message and overview
- `/addbot` - Create a new news bot (interactive setup)
- `/listbots` - Show all your configured bots
- `/deletebot` - Remove a bot permanently
- `/startbot` - Start a stopped bot
- `/stopbot` - Stop a running bot
- `/help` - Show help information

### Creating a News Bot

1. Send `/addbot` to BotFather
2. Follow the interactive setup:
   - Choose a bot name
   - Provide Telegram bot token
   - Select news niche (Tech, Crypto, AI, General, or Custom)
   - Set update frequency (1-24 hours)
   - Choose news sources (default or custom RSS feeds)
   - Set posting preference (manual approval or auto-post)

### Bot Flow

1. Bot fetches news from RSS feeds
2. AI generates 3 tweet suggestions per article
3. Sends suggestions to you via Telegram
4. You choose which tweets to post (or skip)
5. Selected tweets are posted to X (Twitter)

## 🔧 Configuration

### Default RSS Sources

**Technology:**
- TechCrunch
- The Verge
- Ars Technica
- Wired

**Cryptocurrency:**
- CoinDesk
- Cointelegraph
- Decrypt
- Bitcoin Magazine

**AI:**
- VentureBeat AI
- AI News
- O'Reilly Radar
- Synced Review

**General:**
- BBC News
- NPR
- CNN
- Reuters

### Custom RSS Feeds

You can add your own RSS feeds during bot creation or modify the `RSSFetcher` class in `sources/rss_fetcher.py`.

## 🔑 API Requirements

### OpenAI API
- Required for AI tweet generation
- Fallback to template-based tweets if not available
- Get your key from [OpenAI Platform](https://platform.openai.com/api-keys)

### X (Twitter) API
- Required for posting tweets
- Simulated posting if not configured
- Get bearer token from [Twitter Developer Portal](https://developer.twitter.com/)

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**: Check if the Telegram token is correct
2. **No tweets generated**: Verify OpenAI API key in `.env` file
3. **Can't post to X**: Check X Bearer Token configuration
4. **No news articles**: Check RSS feed URLs are accessible

### Logs

Check the console output for detailed error messages and status updates.

## 🚧 Future Enhancements

- [ ] Web dashboard for bot management
- [ ] Database storage instead of YAML
- [ ] Support for more social platforms
- [ ] Advanced filtering and keyword detection
- [ ] Analytics and performance metrics
- [ ] Docker containerization

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review console logs for error messages
3. Open an issue on GitHub

---

**Happy tweeting! 🐦**
