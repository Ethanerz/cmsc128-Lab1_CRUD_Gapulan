import sqlite3

conn = sqlite3.connect('todo.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        due_datetime TEXT,
        priority TEXT NOT NULL,
        tag TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()
print("Database initialized.")