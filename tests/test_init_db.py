from contextlib import closing
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


INIT_DB = Path(__file__).resolve().parents[1] / 'init_db.py'


class InitDbMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / 'todo.db'
        with closing(sqlite3.connect(self.database_path)) as conn:
            conn.executescript('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO users (username, display_name, password_hash)
                VALUES ('alice', 'Alice', 'hash');
                INSERT INTO users (username, display_name, password_hash)
                VALUES ('bob', 'Bob', 'hash');
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due_datetime TEXT,
                    priority TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER NOT NULL REFERENCES users(id)
                );
                INSERT INTO tasks (title, priority, tag, user_id)
                VALUES ('Personal task', 'High', 'School', 1);
            ''')

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_initializer(self):
        subprocess.run(
            [sys.executable, str(INIT_DB)],
            cwd=self.temp_dir.name,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_migration_preserves_personal_tasks_and_is_repeatable(self):
        self.run_initializer()

        with closing(sqlite3.connect(self.database_path)) as conn:
            conn.execute('PRAGMA foreign_keys = ON')
            self.assertEqual(
                conn.execute(
                    'SELECT title, user_id, list_id FROM tasks'
                ).fetchone(),
                ('Personal task', 1, None),
            )
            task_columns = {
                row[1]: row for row in conn.execute('PRAGMA table_info(tasks)')
            }
            self.assertEqual(task_columns['list_id'][3], 0)
            self.assertEqual(
                conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
                2,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name IN "
                    "('collaborative_lists', 'collaborative_list_members') "
                    "ORDER BY name"
                ).fetchall(),
                [('collaborative_list_members',), ('collaborative_lists',)],
            )

            conn.execute(
                'INSERT INTO collaborative_lists (name, owner_id) VALUES (?, ?)',
                ('Study group', 1),
            )
            list_id = conn.execute(
                'SELECT id FROM collaborative_lists WHERE name = ?',
                ('Study group',),
            ).fetchone()[0]
            conn.execute(
                'INSERT INTO collaborative_list_members (list_id, user_id) '
                'VALUES (?, ?)',
                (list_id, 2),
            )
            conn.execute(
                'INSERT INTO tasks (title, priority, tag, user_id, list_id) '
                'VALUES (?, ?, ?, ?, ?)',
                ('Shared task', 'Low', 'School', 1, list_id),
            )
            conn.commit()

        self.run_initializer()

        with closing(sqlite3.connect(self.database_path)) as conn:
            self.assertEqual(
                conn.execute(
                    'SELECT title, user_id, list_id FROM tasks ORDER BY id'
                ).fetchall(),
                [('Personal task', 1, None), ('Shared task', 1, list_id)],
            )
            self.assertEqual(
                conn.execute(
                    'SELECT list_id, user_id FROM collaborative_list_members'
                ).fetchall(),
                [(list_id, 2)],
            )

    def test_foreign_keys_and_membership_uniqueness(self):
        self.run_initializer()

        with closing(sqlite3.connect(self.database_path)) as conn:
            conn.execute('PRAGMA foreign_keys = ON')
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    'INSERT INTO collaborative_lists (name, owner_id) '
                    'VALUES (?, ?)',
                    ('Invalid owner', 999),
                )
            conn.execute(
                'INSERT INTO collaborative_lists (name, owner_id) VALUES (?, ?)',
                ('Study group', 1),
            )
            list_id = conn.execute(
                'SELECT id FROM collaborative_lists'
            ).fetchone()[0]
            conn.execute(
                'INSERT INTO collaborative_list_members (list_id, user_id) '
                'VALUES (?, ?)',
                (list_id, 2),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    'INSERT INTO collaborative_list_members (list_id, user_id) '
                    'VALUES (?, ?)',
                    (list_id, 2),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    'INSERT INTO tasks (title, priority, tag, user_id, list_id) '
                    'VALUES (?, ?, ?, ?, ?)',
                    ('Invalid list', 'Low', 'School', 1, 999),
                )


if __name__ == '__main__':
    unittest.main()
