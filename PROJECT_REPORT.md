# RunLog — Personal Running Tracker

## Abstract

RunLog is a web-based personal running tracker built with Python Flask and SQLite. It demonstrates relational database concepts through a normalized run-type lookup table, a transaction table, primary and foreign keys, check constraints, joins, aggregate functions, and parameterized SQL.

## Introduction

Many runners record distance and time in unstructured notes. RunLog provides a simple, searchable history with derived duration and pace information while keeping the data in a relational database.

## Problem Statement

A user needs a reliable way to save running sessions, review progress, edit mistakes, delete records, and export data without manually calculating pace or maintaining repeated run-type text.

## Objectives

1. Store valid running sessions in SQLite.
2. Demonstrate normalized relational tables and foreign keys.
3. Calculate duration and pace consistently.
4. Provide CRUD operations and dashboard aggregates.
5. Export the history in an Excel-compatible CSV format.

## Scope

Implemented scope includes run dates, preset/custom distances, duration, run types, notes, dashboard statistics, history, editing, deletion, and CSV export. Authentication, cloud synchronization, GPS tracking, charts, and mobile applications are outside the implemented scope.

## Hardware and Software Requirements

- Any computer capable of running Python 3 and a modern web browser.
- Python 3.9 or later, Flask 3.x, SQLite 3, HTML5, CSS3, and Bootstrap 5.3.
- No separate database server is required because SQLite is embedded.

## Technology Stack

The backend uses Python 3, Flask, and the standard `sqlite3`, `csv`, and `io` libraries. The frontend uses HTML5, CSS3, Bootstrap 5.3 dark mode, and a small vanilla JavaScript function.

## Database Schema

### `run_types` (lookup table)

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | Primary key, auto-increment |
| name | TEXT | NOT NULL, UNIQUE |

Seed rows are `Easy Run`, `Tempo / Pace`, `Interval / Track`, `Long Run`, and `Race`.

### `runs` (main transaction table)

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | Primary key, auto-increment |
| run_date | TEXT | NOT NULL, ISO `YYYY-MM-DD` |
| distance_km | REAL | NOT NULL, CHECK greater than 0 |
| duration_seconds | INTEGER | NOT NULL, CHECK greater than 0 |
| type_id | INTEGER | NOT NULL, default 1, foreign key |
| notes | TEXT | Optional |

## ER Diagram Description and Normalization

One `run_types` row can relate to many `runs` rows, so the relationship is one-to-many: `run_types.id` is referenced by `runs.type_id`. The foreign key is enabled with `PRAGMA foreign_keys = ON`.

The design is in 1NF because every field stores one atomic value. It is in 2NF because the single-column primary keys mean every non-key column depends on the whole key. It is in 3NF because run-type names are stored once in `run_types`; `runs` stores only the foreign-key identifier and has no transitive dependency on the type name.

## System Design and Modules

- **Database module:** `get_db()` opens SQLite, configures `sqlite3.Row`, and enables foreign keys; `init_db()` creates and seeds tables.
- **Helper module:** `format_duration()` converts seconds to a readable time; `calculate_pace()` divides duration by distance.
- **Dashboard module:** `/` performs an `INNER JOIN` for history and one aggregate query for summary cards.
- **CRUD module:** `/add`, `/edit/<id>`, and `/delete/<id>` insert, update, and delete records.
- **Export module:** `/export` joins data, writes CSV rows to `io.StringIO`, prepends a UTF-8 BOM, and downloads the file.
- **Validation module:** `read_run_form()` converts minutes and seconds to total seconds and checks positive distance and duration.

## Exact SQL Queries Used

### DDL

```sql
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
```

### DML

```sql
INSERT OR IGNORE INTO run_types (name) VALUES (?);
INSERT INTO runs (run_date, distance_km, duration_seconds, type_id, notes)
VALUES (?, ?, ?, ?, ?);
UPDATE runs
SET run_date = ?, distance_km = ?, duration_seconds = ?, type_id = ?, notes = ?
WHERE id = ?;
DELETE FROM runs WHERE id = ?;
```

### Join and aggregate queries

```sql
SELECT runs.id, runs.run_date, runs.distance_km, runs.duration_seconds,
       runs.notes, run_types.name AS type_name
FROM runs
INNER JOIN run_types ON runs.type_id = run_types.id
ORDER BY runs.run_date DESC, runs.id DESC;
```

```sql
SELECT COUNT(id) AS total_runs,
       COALESCE(SUM(distance_km), 0) AS total_distance,
       COALESCE(SUM(duration_seconds), 0) AS total_seconds
FROM runs;
```

The average pace is calculated in Python from the aggregate duration and distance, avoiding division by zero for an empty table.

## Test Cases

| Input | Expected Output | Actual Behavior |
|---|---|---|
| Valid 5K, 30 minutes | New row is inserted and success alert appears | Works as expected |
| Distance 0 | Insert/update is rejected with validation alert | Works as expected |
| Duration 0:00 | Insert/update is rejected with validation alert | Works as expected |
| Seconds 60 | Browser constraint and Python validation reject input | Works as expected |
| Edit an existing run | Existing row is pre-filled and updated | Works as expected |
| Delete an existing run | Confirmation is shown, then row is removed | Works as expected |
| Open export | UTF-8 BOM CSV downloads with requested columns | Works as expected |
| No runs in database | Cards show zero and pace shows an em dash | Works as expected |

## Limitations

The implemented application has no login system, pagination, server-side date-range reports, GPS route data, or multi-user separation. SQLite is suitable for this small local project but is not intended here as a high-concurrency production service.

## Proposed Future Enhancements

Future versions could add user authentication, charts, training goals, route/GPS import, date filters, pagination, cloud backups, and a REST API. These are proposals only and are not implemented in the current project.

## Conclusion

RunLog meets the requirements of a compact DBMS mini-project while remaining easy to explain. Its explicit SQL, normalized schema, constraints, joins, aggregates, and parameterized inputs provide practical examples of core relational database principles.
