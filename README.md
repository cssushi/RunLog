# RunLog — Personal Running Tracker

RunLog is a beginner-friendly Flask and SQLite DBMS mini-project for recording runs, calculating pace, and exporting history to an Excel-compatible CSV file.

## Setup and run

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in a browser. The first start automatically creates `database.db`, enables foreign keys, creates both tables, and inserts the five run types.

## File-by-file guide

- `app.py`: Flask routes, database connection, schema initialization, parameterized CRUD/aggregate SQL, validation, pace helpers, and CSV export.
- `requirements.txt`: The only external dependency, Flask.
- `templates/base.html`: Shared dark Bootstrap layout, navbar, flash alerts, and CSV link.
- `templates/index.html`: Dashboard cards, add-run form, distance presets, and joined run-history table.
- `templates/edit_run.html`: Pre-filled edit form with duration splitting and custom-distance handling.
- `static/style.css`: Small set of project-specific spacing and card styles.
- `PROJECT_REPORT.md`: Academic project documentation and viva preparation notes.
- `database.db`: Generated automatically at runtime; it is not required in the source files.

## Database idea

`run_types` is a normalized lookup table. Each row in `runs` stores a `type_id` foreign key rather than repeating the run-type text. The application uses `?` placeholders for every user-supplied SQL value.
