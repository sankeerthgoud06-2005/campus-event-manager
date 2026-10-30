from datetime import date, timedelta
from pathlib import Path
import csv
import io
import os
import sqlite3

from flask import Flask, abort, flash, make_response, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-development-key-change-before-deploying")
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "events.db"
EVENT_STATUSES = ["Upcoming", "Cancelled"]


def db_connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with db_connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            event_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            venue TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK(capacity > 0),
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Upcoming',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS attendees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department TEXT NOT NULL DEFAULT '',
            checked_in INTEGER NOT NULL DEFAULT 0,
            registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_id, email)
        )""")
        if db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
            today = date.today()
            db.executemany(
                "INSERT INTO events (title, category, event_date, start_time, venue, capacity, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    ("Campus Tech Meetup", "Technology", (today + timedelta(days=7)).isoformat(), "10:00", "Seminar Hall A", 80, "A sample event. Edit it or replace it with your own campus event."),
                    ("Project Showcase", "Academic", (today + timedelta(days=14)).isoformat(), "13:30", "Main Auditorium", 120, "A sample event for student projects and demos."),
                ],
            )


def fetch_event(event_id):
    with db_connect() as db:
        event = db.execute("""SELECT e.*, COUNT(a.id) AS attendee_count,
            SUM(CASE WHEN a.checked_in = 1 THEN 1 ELSE 0 END) AS checkin_count
            FROM events e LEFT JOIN attendees a ON a.event_id = e.id
            WHERE e.id = ? GROUP BY e.id""", (event_id,)).fetchone()
    if event is None:
        abort(404)
    return event


def fetch_events():
    with db_connect() as db:
        return db.execute("""SELECT e.*, COUNT(a.id) AS attendee_count,
            SUM(CASE WHEN a.checked_in = 1 THEN 1 ELSE 0 END) AS checkin_count
            FROM events e LEFT JOIN attendees a ON a.event_id = e.id
            GROUP BY e.id ORDER BY e.event_date, e.start_time""").fetchall()


def event_form_data():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    event_date = request.form.get("event_date", "").strip()
    start_time = request.form.get("start_time", "").strip()
    venue = request.form.get("venue", "").strip()
    description = request.form.get("description", "").strip()
    try:
        date.fromisoformat(event_date)
    except ValueError:
        raise ValueError("Choose a valid event date.")
    if not all([title, category, start_time, venue]):
        raise ValueError("Title, category, time, and venue are required.")
    try:
        capacity = int(request.form.get("capacity", ""))
        if capacity < 1:
            raise ValueError
    except ValueError:
        raise ValueError("Capacity must be a whole number greater than zero.")
    status = request.form.get("status", "Upcoming")
    if status not in EVENT_STATUSES:
        raise ValueError("Choose a valid event status.")
    return (title, category, event_date, start_time, venue, capacity, description, status)


@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()
    events = fetch_events()
    visible = [e for e in events if
               (not query or query.casefold() in e["title"].casefold() or query.casefold() in e["venue"].casefold()) and
               (not category or e["category"] == category) and
               (not status or ("Cancelled" if e["status"] == "Cancelled" else "Completed" if e["event_date"] < date.today().isoformat() else "Upcoming") == status)]
    categories = sorted({e["category"] for e in events})
    upcoming = sum(e["status"] == "Upcoming" and e["event_date"] >= date.today().isoformat() for e in events)
    attendees = sum(e["attendee_count"] for e in events)
    with db_connect() as db:
        checked_in = db.execute("SELECT COUNT(*) FROM attendees WHERE checked_in=1").fetchone()[0]
    return render_template("index.html", events=visible, categories=categories, query=query,
                           selected_category=category, selected_status=status, total=len(events),
                           upcoming=upcoming, attendees=attendees, checked_in=checked_in,
                           today=date.today().isoformat())


@app.route("/events/new", methods=["GET", "POST"])
def create_event():
    if request.method == "POST":
        try:
            values = event_form_data()
        except ValueError as error:
            flash(str(error), "error")
            return render_template("event_form.html", event=None, statuses=EVENT_STATUSES)
        with db_connect() as db:
            cursor = db.execute("INSERT INTO events (title, category, event_date, start_time, venue, capacity, description, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", values)
            event_id = cursor.lastrowid
        flash("Event created. Share its registration page with attendees.", "success")
        return redirect(url_for("event_detail", event_id=event_id))
    return render_template("event_form.html", event=None, statuses=EVENT_STATUSES)


@app.route("/events/<int:event_id>")
def event_detail(event_id):
    event = fetch_event(event_id)
    with db_connect() as db:
        attendees = db.execute("SELECT * FROM attendees WHERE event_id=? ORDER BY registered_at DESC", (event_id,)).fetchall()
    return render_template("event_detail.html", event=event, attendees=attendees,
                           is_full=event["attendee_count"] >= event["capacity"], today=date.today().isoformat())


@app.route("/events/<int:event_id>/register", methods=["POST"])
def register_attendee(event_id):
    event = fetch_event(event_id)
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    department = request.form.get("department", "").strip()
    if event["status"] == "Cancelled":
        flash("Registration is closed because this event was cancelled.", "error")
    elif event["event_date"] < date.today().isoformat():
        flash("Registration is closed because this event has ended.", "error")
    elif event["attendee_count"] >= event["capacity"]:
        flash("This event has reached its attendee limit.", "error")
    elif not name or not email or "@" not in email:
        flash("Enter your name and a valid email address.", "error")
    else:
        try:
            with db_connect() as db:
                db.execute("INSERT INTO attendees (event_id, name, email, department) VALUES (?, ?, ?, ?)", (event_id, name, email, department))
            flash("Registration successful. See you at the event!", "success")
        except sqlite3.IntegrityError:
            flash("This email is already registered for the event.", "error")
    return redirect(url_for("event_detail", event_id=event_id) + "#register")


@app.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
def edit_event(event_id):
    event = fetch_event(event_id)
    if request.method == "POST":
        try:
            values = event_form_data()
            if values[5] < event["attendee_count"]:
                raise ValueError(f"Capacity cannot be lower than the {event['attendee_count']} current registrations.")
        except ValueError as error:
            flash(str(error), "error")
            return render_template("event_form.html", event=event, statuses=EVENT_STATUSES)
        with db_connect() as db:
            db.execute("UPDATE events SET title=?, category=?, event_date=?, start_time=?, venue=?, capacity=?, description=?, status=? WHERE id=?", (*values, event_id))
        flash("Event updated.", "success")
        return redirect(url_for("event_detail", event_id=event_id))
    return render_template("event_form.html", event=event, statuses=EVENT_STATUSES)


@app.route("/events/<int:event_id>/delete", methods=["POST"])
def delete_event(event_id):
    fetch_event(event_id)
    with db_connect() as db:
        db.execute("DELETE FROM events WHERE id=?", (event_id,))
    flash("Event and its registrations deleted.", "success")
    return redirect(url_for("index"))


@app.route("/attendees/<int:attendee_id>/checkin", methods=["POST"])
def toggle_checkin(attendee_id):
    with db_connect() as db:
        attendee = db.execute("SELECT * FROM attendees WHERE id=?", (attendee_id,)).fetchone()
        if attendee is None:
            abort(404)
        db.execute("UPDATE attendees SET checked_in=? WHERE id=?", (0 if attendee["checked_in"] else 1, attendee_id))
    return redirect(url_for("event_detail", event_id=attendee["event_id"]) + "#attendees")


@app.route("/events/<int:event_id>/attendees.csv")
def export_attendees(event_id):
    event = fetch_event(event_id)
    with db_connect() as db:
        attendees = db.execute("SELECT name, email, department, checked_in, registered_at FROM attendees WHERE event_id=? ORDER BY name", (event_id,)).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Department", "Checked in", "Registered at"])
    writer.writerows([[a["name"], a["email"], a["department"], "Yes" if a["checked_in"] else "No", a["registered_at"]] for a in attendees])
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename=event-{event_id}-attendees.csv"
    return response


init_db()

if __name__ == "__main__":
    app.run(debug=True)
