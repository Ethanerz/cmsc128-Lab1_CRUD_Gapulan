from contextlib import closing
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parents[1]
INIT_DB = APP_DIR / 'init_db.py'
os.environ.setdefault('SECRET_KEY', 'test-secret')
sys.path.insert(0, str(APP_DIR))
import app as app_module


class CollaborativeListApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / 'todo.db'
        subprocess.run(
            [sys.executable, str(INIT_DB)],
            cwd=self.temp_dir.name,
            check=True,
            capture_output=True,
            text=True,
        )
        with closing(sqlite3.connect(self.database_path)) as conn:
            conn.executemany(
                '''INSERT INTO users (username, display_name, password_hash)
                   VALUES (?, ?, ?)''',
                [
                    ('owner', 'Owner', 'hash'),
                    ('member', 'Member', 'hash'),
                    ('stranger', 'Stranger', 'hash'),
                    ('member@example.com', 'Email Member', 'hash'),
                ],
            )
            conn.commit()

        app_module.app.config['TESTING'] = True
        self.database_patch = patch.object(app_module, 'get_db', self.connect_db)
        self.database_patch.start()
        self.owner_client = app_module.app.test_client()
        self.member_client = app_module.app.test_client()
        self.stranger_client = app_module.app.test_client()
        self.authenticate(self.owner_client, 1)
        self.authenticate(self.member_client, 2)
        self.authenticate(self.stranger_client, 3)

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def connect_db(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    @staticmethod
    def authenticate(client, user_id):
        with client.session_transaction() as user_session:
            user_session['user_id'] = user_id

    def create_list(self):
        response = self.owner_client.post(
            '/lists',
            json={'name': 'Study group', 'owner_id': 2},
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()['id']

    def test_requires_login_for_list_routes(self):
        client = app_module.app.test_client()
        self.assertEqual(client.get('/lists').status_code, 401)
        self.assertEqual(client.post('/lists', json={'name': 'Group'}).status_code, 401)

    def test_create_and_list_only_owned_or_joined_lists(self):
        list_id = self.create_list()
        with closing(self.connect_db()) as conn:
            created = conn.execute(
                'SELECT owner_id FROM collaborative_lists WHERE id = ?',
                (list_id,),
            ).fetchone()
            self.assertEqual(created['owner_id'], 1)

        self.assertEqual(
            [item['id'] for item in self.owner_client.get('/lists').get_json()],
            [list_id],
        )
        self.assertEqual(self.member_client.get('/lists').get_json(), [])
        self.assertEqual(self.stranger_client.get('/lists').get_json(), [])

        with closing(self.connect_db()) as conn:
            conn.execute(
                'INSERT INTO collaborative_list_members (list_id, user_id) '
                'VALUES (?, ?)',
                (list_id, 2),
            )
            conn.commit()

        self.assertEqual(
            [item['id'] for item in self.member_client.get('/lists').get_json()],
            [list_id],
        )
        self.assertEqual(self.stranger_client.get('/lists').get_json(), [])

    def test_only_owner_can_invite_and_unknown_users_are_rejected(self):
        list_id = self.create_list()

        non_owner_response = self.member_client.post(
            f'/lists/{list_id}/members',
            json={'username': 'stranger'},
        )
        self.assertEqual(non_owner_response.status_code, 404)

        missing_user_response = self.owner_client.post(
            f'/lists/{list_id}/members',
            json={'username': 'missing'},
        )
        self.assertEqual(missing_user_response.status_code, 404)

        invite_response = self.owner_client.post(
            f'/lists/{list_id}/members',
            json={'username': 'member'},
        )
        self.assertEqual(invite_response.status_code, 201)
        self.assertEqual(invite_response.get_json()['user_id'], 2)
        self.assertEqual(
            [item['id'] for item in self.member_client.get('/lists').get_json()],
            [list_id],
        )

        duplicate_response = self.owner_client.post(
            f'/lists/{list_id}/members',
            json={'username': 'member'},
        )
        self.assertEqual(duplicate_response.status_code, 200)

        email_shaped_username_response = self.owner_client.post(
            f'/lists/{list_id}/members',
            json={'email': 'member@example.com'},
        )
        self.assertEqual(email_shaped_username_response.status_code, 201)
        self.assertEqual(email_shaped_username_response.get_json()['user_id'], 4)

    def test_invalid_list_data_and_nonexistent_list(self):
        self.assertEqual(
            self.owner_client.post('/lists', json={'name': '   '}).status_code,
            400,
        )
        self.assertEqual(
            self.owner_client.post('/lists/999/members', json={'username': 'member'}).status_code,
            404,
        )

    def test_invite_uses_email_column_when_available(self):
        with closing(self.connect_db()) as conn:
            conn.execute('ALTER TABLE users ADD COLUMN email TEXT')
            conn.execute(
                'UPDATE users SET email = ? WHERE id = ?',
                ('member@real.example', 2),
            )
            conn.commit()

        list_id = self.create_list()
        response = self.owner_client.post(
            f'/lists/{list_id}/members',
            json={'email': 'member@real.example'},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['user_id'], 2)


if __name__ == '__main__':
    unittest.main()
