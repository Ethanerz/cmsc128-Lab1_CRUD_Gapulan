# CMSC 128 Lab 3: Multi-Account Collaborative To-Do List

This Flask to-do application combines account registration and login with personal and collaborative task lists. Users can manage their personal tasks, create collaborative lists, invite other registered users, and work on tasks in lists they own or have joined.

## Activity 1 and Activity 2 Integration

Activity 2 was built on top of the Activity 1 to-do application in the same codebase, rather than developed as a separate branch that needed to be merged. The CRUD page and task operations were integrated with Activity 2 registration and login; no branch merge or merge-conflict resolution was needed for this integration.

## Tech Stack

| Layer | Choice |
| --- | --- |
| Backend | Python + Flask |
| Authentication | Flask signed sessions |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` |

## Data Model

The database is `todo.db`, initialized by `init_db.py`.

- **`users`** stores accounts, unique usernames, display names, and password hashes. Plaintext passwords are not stored.
- **`tasks`** stores task fields and a required `user_id` foreign key to `users.id`. A personal task has a `NULL` `list_id`. For a shared task, `list_id` refers to the collaborative list and `user_id` records the user who created it.
- **`collaborative_lists`** stores each list’s name and required `owner_id` foreign key to `users.id`.
- **`collaborative_list_members`** links users to lists with a composite primary key on `(list_id, user_id)`. The list owner is also inserted as a member.

Foreign keys are enabled for database initialization and each application database connection. The initialization script is repeatable: it adds the collaborative-list tables and the nullable `tasks.list_id` column without deleting existing user accounts or personal tasks.

## Authentication and Access Control

Registration hashes passwords before inserting accounts. Login verifies the submitted password against the stored hash and saves the authenticated user's ID and display name in Flask's signed session. The session is configured to be permanent for 30 days. Keep the same secret `SECRET_KEY` across application restarts so existing session cookies remain verifiable.

Task and collaborative-list endpoints require a login. Authorization is enforced on the server using the session user ID:

- Personal task reads filter by `tasks.user_id` and `tasks.list_id IS NULL`.
- A shared-list read or create checks that the user owns the list or has a row in `collaborative_list_members`.
- Task updates and deletes match the task ID and also require either personal ownership or membership/ownership of the task's collaborative list.
- List reads return only lists owned by or joined by the current user.
- Only a collaborative-list owner can invite another registered account.
- Missing and inaccessible lists/tasks return a 404 response rather than exposing another user's data.

## API Examples

All task and list endpoints below require the logged-in Flask session.

| Method and path | Purpose | Server-side authorization |
| --- | --- | --- |
| `GET /lists` | List collaborative lists visible to the current user | Filters by `owner_id = session user ID` or membership |
| `POST /lists` | Create a collaborative list with JSON `{"name":"Study group"}` | Sets `owner_id` from the session and adds the owner as a member |
| `POST /lists/<list_id>/members` | Invite with JSON `{"username":"alex"}` or `{"email":"alex@example.com"}` | Requires the session user to own the list and the invited account to exist |
| `GET /tasks` | Get personal tasks | Filters by session `user_id` and `list_id IS NULL` |
| `GET /tasks?list_id=<id>` | Get shared-list tasks | Requires the session user to own or belong to the selected list |
| `POST /tasks` | Create a personal task | Sets `user_id` from the session; ignores any browser-supplied owner ID |
| `POST /tasks` with `list_id` | Create a shared-list task | Requires owner/member access to that list; records the creator from the session |
| `PUT /tasks/<task_id>` | Update a task | Matches task ID and requires personal ownership or shared-list access |
| `DELETE /tasks/<task_id>` | Delete a task | Matches task ID and requires personal ownership or shared-list access |

The current `users` schema identifies accounts by username and does not contain a dedicated email column. The invitation endpoint accepts an `email` field when an email column exists; with the current schema it looks up that value as a username (so an email-shaped username can be used).

Registration and profile management use `POST /register` and `GET`/`POST /profile`. Login uses `GET`/`POST /login`, and `POST /logout` clears the current session.

## Local Installation and Run

1. Open a terminal in the project root.
2. Optionally create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Create a `.env` file containing a `SECRET_KEY`. Generate a random value with:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   Add the generated value to `.env`:

   ```text
   SECRET_KEY=your-generated-secret-key
   ```

5. Initialize or migrate the local database:

   ```bash
   python init_db.py
   ```

6. Start the Flask application:

   ```bash
   python app.py
   ```

7. Open <http://127.0.0.1:5000/> in a browser.

The local database (`todo.db`) and `.env` file are not included in the repository. Keep the database file to preserve accounts and tasks.

## Tests

The schema migration and API tests use Python's standard `unittest` runner:

```bash
python -m unittest discover -s tests -v
```

The tests cover schema migration repeatability, personal-task preservation, foreign-key constraints, collaborative list membership, and access control for task and list routes.
