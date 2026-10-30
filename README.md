# Gather — Campus Event Manager

A Flask and SQLite web app for organizing campus events from creation through attendee check-in. It runs locally and does not need an external API or cloud account.

## Features

- Create, edit, search, filter, and delete campus events
- Store date, time, venue, category, description, capacity, and event status
- Public event detail page with attendee self-registration
- Prevent duplicate registrations by email and reject registration when an event is full, cancelled, or over
- Track attendee departments and check people in
- Export an event's attendee list as a CSV file
- Dashboard counts and registration progress bars
- SQLite database and two sample events are created on first run
- Responsive pages for desktop and mobile

## Requirements

- Python 3.10 or newer
- Internet access only for optional Google Fonts styling; the app's features work offline

## Quick start on Windows

1. Extract this folder and open it in VS Code.
2. Double-click `run.bat`, or open the VS Code terminal in this folder and run:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

3. Open **http://127.0.0.1:5000** in your browser. Stop the server with `Ctrl+C`.

## Run on macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000**.

## Try the app

The home page starts with two sample events. Open an event, use its registration form to add an attendee, then mark the attendee as present in the attendee list. The CSV button downloads the current attendee list for that event. You can edit or delete the sample events and create your own.

The event detail page contains both the attendee registration form and event management controls. This project is designed as a local portfolio demo; it does not include admin accounts or access control, so do not expose it publicly with real attendee information.

## Upload to GitHub

Create an empty repository on GitHub (for example, `campus-event-manager`). In the VS Code terminal, from this project folder, run these commands and replace the username:

```bash
git init
git add .
git commit -m "Build campus event manager"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/campus-event-manager.git
git push -u origin main
```

The `.gitignore` keeps the virtual environment and local attendee database out of Git.

## Project structure

```text
campus-event-manager/
├── app.py                     # Flask routes, validation, and SQLite database
├── requirements.txt           # Python dependency
├── run.bat                    # Windows quick start
├── README.md                  # Setup and GitHub instructions
├── .gitignore
├── .env.example
├── templates/
│   ├── index.html             # Dashboard, search, filters, event cards
│   ├── event_form.html        # Create and edit events
│   └── event_detail.html      # Event details, registration, check-in, CSV link
└── static/
    └── style.css              # Responsive styling
```

## Portfolio description

Gather is a campus event management web application built with Flask and SQLite. It lets organizers create and manage events, collect attendee registrations with capacity and duplicate-email checks, track check-ins, and export attendee lists to CSV.

## Before deploying publicly

Set a strong `FLASK_SECRET_KEY`, add administrator authentication and CSRF protection, and run with a production WSGI server. The Flask development server included here is for local development only.
