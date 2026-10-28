# Cheatbot – Smart Developer Launcher

A polished Flask-based developer launcher and dashboard for searching and opening frequently used websites, tools, and local applications from one place.

## Features

- Smart search with instant suggestions
- Category-based browsing
- Quick launch cards
- Favorites and recent history
- Resource creation form
- Local application launch with safe allowlist checks
- Dark and light theme
- Optional login and registration
- Basic analytics dashboard

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Run the app:
   python app.py
4. Open http://127.0.0.1:5000

## Project layout

- app.py
- config.py
- routes/
- templates/
- static/
- database/

## Notes

- Local application launching is validated against a safe allowlist.
- If a local app is missing or not allowed, the app falls back to the configured website URL where possible.
- Passwords are stored as hashes using Werkzeug.
