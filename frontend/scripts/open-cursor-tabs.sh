#!/usr/bin/env bash
# Open IndieFund role demo pages in Cursor Simple Browser tabs (not Chrome).
set -euo pipefail

BASE="${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:5173}"

open_in_cursor() {
  local url="$1"
  local encoded
  encoded=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$url")
  if command -v cursor >/dev/null 2>&1; then
    cursor --open-url "vscode://vscode.simple-browser/show?url=${encoded}" >/dev/null 2>&1 || true
  elif command -v code >/dev/null 2>&1; then
    code --open-url "vscode://vscode.simple-browser/show?url=${encoded}" >/dev/null 2>&1 || true
  else
    echo "Install Cursor CLI or open manually: $url"
    return 1
  fi
}

echo "Opening Cursor Simple Browser tabs..."
echo ""
echo "Log in on Profile (password demo12345 for all demo accounts):"
echo "  Fan    → demo_fan    then use Discover tab"
echo "  Artist → luna_lane   then use Home dashboard"
echo "  Host   → team_host   then use Spaces tab"
echo ""
echo "Note: Simple Browser shares one session — log out in Profile before switching accounts."
echo ""

open_in_cursor "${BASE}/?page=profile"
sleep 0.4
open_in_cursor "${BASE}/?page=discover"
sleep 0.4
open_in_cursor "${BASE}/?artist=luna_lane"
sleep 0.4
open_in_cursor "${BASE}/?page=spaces"

echo "Opened Profile, Discover (fan), Artist public page, and Spaces (host) in Cursor tabs."
