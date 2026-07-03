# Aider Handoff

Project directory:

```bash
cd /Users/dannylinsen/Desktop/MusicPlatform/indie_artist_platform
```

Open Aider with the 7b or 14b Ollama model:

```bash
./aid7
./aid14
```

Both commands start an interactive Aider session from the repo root and automatically run:

```text
/run git status
```

The repo includes `.aider.conf.yml` and `.aiderignore` so Aider can read the project context while staying out of generated files, local databases, virtualenvs, build output, and private `.env` files.

Editable project scope:

- `backend/`
- `frontend/`
- top-level project docs and config files

Do not edit generated or private local files covered by `.aiderignore`.

Before handing work back, run:

```bash
backend/.venv/bin/python backend/manage.py check
backend/.venv/bin/python backend/manage.py test
npm --prefix frontend run build
```

Local preview:

```bash
cd backend
.venv/bin/python manage.py runserver localhost:8000
```

```bash
cd frontend
npm run dev -- --host localhost
```

Preview URL: `http://localhost:5173/`
