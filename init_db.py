import sqlite3

conn = sqlite3.connect('todo.db')
conn.execute('PRAGMA foreign_keys = ON')
cursor = conn.cursor()

try:
    conn.execute('BEGIN IMMEDIATE')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    task_table = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'tasks'"
    ).fetchone()
    if task_table:
        task_columns = {
            row[1]: row for row in cursor.execute('PRAGMA table_info(tasks)')
        }
        if 'user_id' not in task_columns:
            cursor.execute('DROP TABLE tasks')
        else:
            foreign_keys = cursor.execute('PRAGMA foreign_key_list(tasks)').fetchall()
            has_user_foreign_key = any(
                row[2] == 'users' and row[3] == 'user_id' and row[4] == 'id'
                for row in foreign_keys
            )
            if not task_columns['user_id'][3] or not has_user_foreign_key:
                raise RuntimeError(
                    'The existing tasks table has an incompatible user_id schema.'
                )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_datetime TEXT,
            priority TEXT NOT NULL,
            tag TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER NOT NULL REFERENCES users(id)
        )
    ''')
    conn.commit()
except Exception:
    conn.rollback()
    raise
finally:
    conn.close()

print("Database initialized.")