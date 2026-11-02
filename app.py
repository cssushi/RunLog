import csv
import io
import os
import sqlite3
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, send_file, url_for


app = Flask(__name__)
app.secret_key = "runlog-development-key"
DATABASE = os.path.join(app.root_path, "database.db")


def get_db():
    """Open SQLite and return rows that can be read by column name."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    """Create the normalized tables and seed the lookup values."""
    connection = get_db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS run_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT NOT NULL,
            distance_km REAL NOT NULL CHECK(distance_km > 0),
            duration_seconds INTEGER NOT NULL CHECK(duration_seconds > 0),
            type_id INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            FOREIGN KEY (type_id) REFERENCES run_types (id)
        );
        """
    )
    run_types = [
        ("Easy Run",),
        ("Tempo / Pace",),
        ("Interval / Track",),
        ("Long Run",),
        ("Race",),
    ]
    connection.executemany(
        "INSERT OR IGNORE INTO run_types (name) VALUES (?)", run_types
    )
    connection.commit()
    connection.close()


def format_duration(seconds):
    """Format seconds as MM:SS, or HH:MM:SS for runs lasting an hour or more."""
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def calculate_pace(seconds, distance_km):
    """Return the average time needed to cover one kilometer."""
    if not distance_km:
        return "—"
    pace_seconds = round(float(seconds) / float(distance_km))
    minutes, remaining_seconds = divmod(pace_seconds, 60)
    return f"{minutes:02d}:{remaining_seconds:02d} /km"


def format_date_parts(run_date):
    """Return display-friendly month, day, and year values for an ISO date."""
    parsed_date = datetime.strptime(run_date, "%Y-%m-%d")
    return parsed_date.strftime("%b"), parsed_date.strftime("%d"), parsed_date.strftime("%Y")


def read_run_form():
    """Read and validate the common add/edit form fields."""
    distance_choice = request.form.get("distance_choice", "")
    distance_value = request.form.get("custom_distance", "") if distance_choice == "custom" else distance_choice
    try:
        distance_km = float(distance_value)
        minutes = int(request.form.get("minutes", "0"))
        seconds = int(request.form.get("seconds", "0"))
        type_id = int(request.form.get("type_id", "0"))
    except (TypeError, ValueError):
        raise ValueError("Please enter valid numeric values.")

    total_seconds = (minutes * 60) + seconds
    if distance_km <= 0:
        raise ValueError("Distance must be greater than 0 km.")
    if minutes < 0 or seconds < 0 or seconds > 59 or total_seconds <= 0:
        raise ValueError("Duration must be greater than 0, with seconds between 0 and 59.")
    run_date = request.form.get("run_date", "")
    if not run_date:
        raise ValueError("Please choose a date.")
    try:
        datetime.strptime(run_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Please enter a valid date.")
    if type_id <= 0:
        raise ValueError("Please choose a run type.")

    return (
        run_date,
        distance_km,
        total_seconds,
        type_id,
        request.form.get("notes", "").strip(),
    )


@app.context_processor
def utility_processor():
    return {
        "format_duration": format_duration,
        "calculate_pace": calculate_pace,
        "format_date_parts": format_date_parts,
    }


@app.route("/")
def index():
    connection = get_db()
    runs = connection.execute(
        """
        SELECT runs.id, runs.run_date, runs.distance_km, runs.duration_seconds,
               runs.notes, run_types.name AS type_name
        FROM runs
        INNER JOIN run_types ON runs.type_id = run_types.id
        ORDER BY runs.run_date DESC, runs.id DESC
        """
    ).fetchall()
    stats = connection.execute(
        """
        SELECT COUNT(id) AS total_runs,
               COALESCE(SUM(distance_km), 0) AS total_distance,
               COALESCE(SUM(duration_seconds), 0) AS total_seconds
        FROM runs
        """
    ).fetchone()
    run_types = connection.execute(
        "SELECT id, name FROM run_types ORDER BY id"
    ).fetchall()
    connection.close()
    average_pace = calculate_pace(stats["total_seconds"], stats["total_distance"])
    return render_template(
        "index.html",
        runs=runs,
        stats=stats,
        average_pace=average_pace,
        run_types=run_types,
        today=date.today().isoformat(),
    )


@app.route("/add", methods=["POST"])
def add_run():
    connection = None
    try:
        run_data = read_run_form()
        connection = get_db()
        valid_type = connection.execute(
            "SELECT id FROM run_types WHERE id = ?", (run_data[3],)
        ).fetchone()
        if valid_type is None:
            raise ValueError("Please choose a valid run type.")
        connection.execute(
            """
            INSERT INTO runs
                (run_date, distance_km, duration_seconds, type_id, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            run_data,
        )
        connection.commit()
        connection.close()
        connection = None
        flash("Run logged successfully.", "success")
    except ValueError as error:
        flash(str(error), "danger")
    finally:
        if connection is not None:
            connection.close()
    return redirect(url_for("index"))


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_run(id):
    connection = get_db()
    if request.method == "POST":
        try:
            run_data = read_run_form()
            valid_type = connection.execute(
                "SELECT id FROM run_types WHERE id = ?", (run_data[3],)
            ).fetchone()
            if valid_type is None:
                raise ValueError("Please choose a valid run type.")
            connection.execute(
                """
                UPDATE runs
                SET run_date = ?, distance_km = ?, duration_seconds = ?,
                    type_id = ?, notes = ?
                WHERE id = ?
                """,
                run_data + (id,),
            )
            connection.commit()
            connection.close()
            connection = None
            flash("Run updated successfully.", "success")
            return redirect(url_for("index"))
        except ValueError as error:
            flash(str(error), "danger")

    run = connection.execute(
        """
        SELECT id, run_date, distance_km, duration_seconds, type_id, notes
        FROM runs WHERE id = ?
        """,
        (id,),
    ).fetchone()
    run_types = connection.execute(
        "SELECT id, name FROM run_types ORDER BY id"
    ).fetchall()
    connection.close()
    if run is None:
        flash("That run could not be found.", "danger")
        return redirect(url_for("index"))
    return render_template(
        "edit_run.html",
        run=run,
        run_types=run_types,
        minutes=run["duration_seconds"] // 60,
        seconds=run["duration_seconds"] % 60,
    )


@app.route("/delete/<int:id>", methods=["POST"])
def delete_run(id):
    connection = get_db()
    connection.execute("DELETE FROM runs WHERE id = ?", (id,))
    connection.commit()
    connection.close()
    flash("Run deleted.", "success")
    return redirect(url_for("index"))


@app.route("/export")
def export_csv():
    connection = get_db()
    runs = connection.execute(
        """
        SELECT runs.id, runs.run_date, run_types.name AS type_name,
               runs.distance_km, runs.duration_seconds, runs.notes
        FROM runs
        INNER JOIN run_types ON runs.type_id = run_types.id
        ORDER BY runs.run_date DESC, runs.id DESC
        """
    ).fetchall()
    connection.close()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Run Type", "Distance (km)", "Duration", "Pace (/km)", "Notes"])
    for run in runs:
        writer.writerow(
            [
                run["id"],
                run["run_date"],
                run["type_name"],
                f"{run['distance_km']:.2f}",
                format_duration(run["duration_seconds"]),
                calculate_pace(run["duration_seconds"], run["distance_km"]),
                run["notes"] or "",
            ]
        )
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="runlog_export.csv",
    )


init_db()

if __name__ == "__main__":
    app.run(debug=True)
