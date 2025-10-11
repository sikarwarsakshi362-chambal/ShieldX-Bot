# ShieldX Media Protector

This repository contains the ShieldX Telegram bot.

IMPORTANT — Do NOT put secrets (API_ID, API_HASH, BOT_TOKEN) in the repo.
Set the following environment variables in your hosting provider (Koyeb):

- API_ID
- API_HASH
- BOT_TOKEN

Deploy instructions (Koyeb):
1. Create a GitHub repo and push these files.
2. On Koyeb, Create App -> Deploy from GitHub -> select this repo.
3. Build command: pip install -r requirements.txt
4. Run command: python bot.py
5. Set environment variables in Koyeb (Service Settings -> Environment variables):
   - API_ID = 26250263
   - API_HASH = 24b066ce7a9020dfbd69b4dc593993f1
   - BOT_TOKEN = <your-bot-token-here>

Your bot will then run 24x7 on Koyeb. Do NOT share your bot token publicly.
