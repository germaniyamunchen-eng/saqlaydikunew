# Telegram Music And Media Downloader Bot

Professional Telegram bot for downloading videos from TikTok, Instagram, YouTube, Facebook, Twitter/X, plus YouTube-based music search.

The bot is built with Python, aiogram v3, SQLite, yt-dlp, Uzbek UI text, admin statistics, broadcast tools, cooldown protection, logging, and Railway-ready deployment files.

## Features

- TikTok, Instagram, YouTube, Facebook, Twitter/X media downloads
- Music search by song name
- Uzbek language interface
- Inline keyboard UI
- Admin panel with statistics and broadcast
- SQLite database
- Anti-spam cooldown
- Conservative file and duration limits
- Error handling and logs
- Railway 24/7 worker deployment support

## Project Structure

```text
bot.py
config.py
states.py
database/
handlers/
keyboards/
middlewares/
services/
utils/
```

## Local Setup

1. Create a bot with BotFather and copy the token.
2. Copy `.env.example` to `.env`.
3. Fill in:

```env
BOT_TOKEN=your_bot_token
ADMIN_IDS=your_telegram_id
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Make sure `ffmpeg` is installed locally if you want MP3 music extraction.

6. Run the bot:

```bash
python bot.py
```

On this Windows project you can also double-click `start.bat` after `.env` is ready.

## Railway Deployment

1. Push this project to GitHub.
2. Create a Railway project from the GitHub repository.
3. Add environment variables from `.env.example`.
4. Railway will run the worker from the `Procfile`.
5. `nixpacks.toml` installs `ffmpeg`, which is needed for MP3 audio extraction.

## Uzbek Usage Notes

- Video yuklash uchun foydalanuvchi havolani botga yuboradi.
- Musiqa yuklash uchun `Musiqa qidirish` tugmasi bosiladi va qo'shiq nomi yoziladi.
- Admin panel uchun `/admin` buyrug'i ishlatiladi.

## Safe Defaults

- `MAX_FILE_MB=45`
- `MAX_DURATION_SECONDS=900`
- `COOLDOWN_SECONDS=10`
- Playlists are disabled.

These defaults help keep the bot stable on Railway and inside Telegram upload limits.

## Important Notes

- Some platforms can block public download tools or require cookies. If a specific URL fails, try another URL first.
- Keep `yt-dlp` updated because social platforms change their pages frequently.
- Respect platform terms, copyright rules, and local laws.
- Never commit `.env` or your bot token.
