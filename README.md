# Indie Artist Platform Starter

A Django + React starter built around your idea: independent artists, fan subscriptions, artist pages, music uploads, merch, lives, stories, and discovery that feels more like YouTube recommendations than viral TikTok chasing.

## Core idea
- Fans subscribe to artists for $1 or a custom amount.
- Fans can subscribe to up to 50 artists by default.
- After 50 subscriptions, the platform prompts them to extend their limit.
- Artists have Instagram-style profiles with YouTube-style content depth.
- Artists can post updates, upload music, sell merch, go live, share stories, and engage with fans.
- Fans get a discovery feed for similar-but-still-unique artists.
- Artists and fans have separate onboarding paths.

## Tech stack
Backend: Django, Django REST Framework
Frontend: React + Vite
Database: PostgreSQL recommended, SQLite works for first local testing

## Next steps
1. Create a Python virtual environment inside `backend`.
2. Install backend requirements.
3. Run Django migrations.
4. Seed local demo data:

```bash
cd backend
python3 manage.py seed_demo
```

Demo logins all use `demo12345`:
- Fan: `demo_fan`
- Artists: `luna_lane`, `static_harbor`, `mika_north`

5. Start React frontend.

This is a strong planning/code starter, not a finished production app yet.
