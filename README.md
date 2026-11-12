# cse108lab8
lab 8 project


branch off main, name your branches properly, do not commit directly to main, have at least one other person review before merging to main


Names: Hunter Merryman, Jack Semanko, Gavin Parrish

## Getting started

This is the shared Flask/SQLAlchemy foundation and admin flow. Student and
teacher pages are placeholders for the rest of the team; course browsing,
enrollment/drop, rosters, and grade editing are not implemented yet.

On Windows, from the project directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = "replace-this-with-a-long-random-local-secret"
flask --app app init-db
flask --app app seed-demo
flask --app app run --debug
```

Open http://127.0.0.1:5000. The demo admin login is `admin` / `demo-password`.
All demo accounts use that password; examples include student `mnorris` and
teacher `ahepworth`.
The SQLite database is stored in `instance\enrollment.db` and persists across
restarts. `seed-demo` only works when all application tables are empty; it will
not overwrite existing data. The seed follows the example data supplied in the
lab assignment, not the differing grades shown in its mockup.

## Admin and shared model

After signing in as an admin, use Flask-Admin to create, view, edit, and delete
users, courses, and enrollments. Set a password when creating a user; leave it
blank when editing to keep the current one. Passwords are stored as hashes.
Remove dependent enrollments and reassign courses before deleting referenced
records. The admin forms enforce roles and capacity; duplicate enrollments and
invalid grades are also rejected by database constraints.

`app\models.py` defines `User`, `Course`, and `Enrollment`; grades belong to
the enrollment and course counts should be derived from its rows. Teammates
should enforce role and ownership checks on the server and handle enrollment,
capacity, and duplicate requests safely, including concurrent requests.
For another SQL database, set `DATABASE_URL` and install the matching driver.
`init-db` creates missing tables but does not migrate an existing schema.

Run the focused tests with:

```powershell
python -m unittest discover -s tests
```