#!/usr/bin/env bash
# Autonomous Local Show Loop beta — seeds data, verifies APIs, prints login URLs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [[ ! -x .venv/bin/python ]]; then
  echo "Create backend venv first: python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py beta_scene_loop --seed "$@"

echo ""
echo "Optional: start servers in two terminals:"
echo "  cd backend && .venv/bin/python manage.py runserver localhost:8000"
echo "  cd frontend && npm run dev -- --host localhost"
echo ""
echo "Then open http://localhost:5173/?page=my-scene as demo_fan (password demo12345)"
