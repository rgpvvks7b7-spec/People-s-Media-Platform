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

## Local setup
Create a Python virtual environment inside `backend`. Python 3.11 is known to work for this project.

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
```

Demo logins all use `demo12345`:
- Fan: `demo_fan`
- Artists: `luna_lane`, `static_harbor`, `mika_north`

### Autonomous Local Show Loop beta

Seed + verify My Scene and gig notifications in one command:

```bash
cd backend
.venv/bin/python manage.py beta_scene_loop --seed
```

Or from the repo root:

```bash
bash scripts/beta_scene_loop.sh
```

Then log in as `demo_fan` and open [My Scene](http://localhost:5173/?page=my-scene). The command prints pass/fail checks and deep links.

Start the backend:

```bash
cd backend
.venv/bin/python manage.py runserver localhost:8000
```

Start the frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev -- --host localhost
```

Run checks before changing behavior:

```bash
cd backend
.venv/bin/python manage.py check
.venv/bin/python manage.py test
```

```bash
cd frontend
npm run build
```

This is a strong planning/code starter, not a finished production app yet.
