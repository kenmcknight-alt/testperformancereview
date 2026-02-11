# Performance Review Hub

A self-contained HR performance review application built with Flask + SQLite.

## Features

- **HR Admin staff registry** with manager assignment.
- **Organization chart** visualization.
- **Review templates** with question-level responder targeting:
  - reviewer
  - reviewee
  - both
- **Review initiation** by selecting template, reviewer, and reviewee.
- **Role-based response forms** for reviewer and reviewee.
- **Auto status tracking** (`In Progress` / `Completed`) based on required responses.
- **Modern Bootstrap UI** for quick, easy navigation.

## Run with Docker

```bash
docker compose up --build
```

Open: <http://localhost:5000>

## Local Run (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Optional Demo Seed Data

```bash
flask --app app seed
```

Then refresh the app.

## Project Structure

- `app.py` – Flask app, models, routes, and seed command.
- `templates/` – HTML templates.
- `static/` – CSS and JavaScript.
- `Dockerfile` + `docker-compose.yml` – containerized runtime.

## Notes

- Uses SQLite (`performance_review.db`) in the app directory.
- Tables are auto-created at app startup.
