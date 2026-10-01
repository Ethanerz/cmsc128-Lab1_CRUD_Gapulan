# CMSC 128 Lab 2: Authentication and User Access

This project extends a Flask to-do list application with account registration, login, persistent sessions, and profile management. Account data is stored in SQLite, and passwords are hashed before they are saved.

## Overview

The app uses a Flask backend, SQLite database, and a vanilla HTML, CSS, and JavaScript frontend. Users can create an account, sign in, manage their profile, and use the to-do list while signed in.

## Tech Stack


| Layer | Choice |
| --- | --- |
| Backend | Python + Flask |
| Authentication | Flask sessions |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` |

## Features Implemented

- Account registration with username, display name, and required fields
- Unique username validation
- Password hashing before account passwords are stored
- Login with username and password verification
- Persistent Flask session configured for 30 days
- Login-protected home page and task API routes
- Logout that clears the active session
- Profile page for changing username, display name, and password
- Current-password verification and password confirmation when changing a password
- New password minimum length of 8 characters

Password recovery by email or another reset flow is not implemented.

## Project Structure

```text
todo_app/
├── app.py                  # Flask app, authentication, profile, and task routes
├── init_db.py              # Creates the SQLite tasks and users tables
├── requirements.txt        # Python dependencies
├── Readme.md
├── .gitignore              # Excludes local secrets, database, virtualenv, and bytecode
├── templates/
│   ├── index.html          # Signed-in to-do list and account navigation
│   ├── login.html          # Login form
│   ├── register.html       # Account registration form
│   └── profile.html        # Profile and password update form
└── static/
    ├── css/
    │   └── style.css       # Shared page and to-do list styles
    └── js/
        └── app.js          # Client-side to-do list interactions
```

`todo.db`, `.env`, and `venv/` are created or configured locally and are not included in the repository.

## Local Installation

1. Open a terminal in the project root.
2. Create and activate a virtual environment if desired.
3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

4. Create a `.env` file with a `SECRET_KEY`. Generate a random value with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set the generated value in `.env`:

```text
SECRET_KEY=your-generated-secret-key
```

5. Initialize the database:

```bash
python init_db.py
```

6. Run the app:

```bash
python app.py
```

7. Open the browser at:

```text
http://127.0.0.1:5000/
```
