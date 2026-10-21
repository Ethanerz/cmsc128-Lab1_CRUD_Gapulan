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


class TaskAccessApiTests(unittest.TestCase):
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
                    ('outsider', 'Outsider', 'hash'),
                ],
            )
            conn.commit()

        app_module.app.config['TESTING'] = True
        self.database_patch = patch.object(app_module, 'get_db', self.connect_db)
        self.database_patch.start()
        self.owner = app_module.app.test_client()
        self.member = app_module.app.test_client()
        self.outsider = app_module.app.test_client()
        self.authenticate(self.owner, 1)
        self.authenticate(self.member, 2)
        self.authenticate(self.outsider, 3)
        self.list_id = self.create_collaborative_list()

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

    def create_collaborative_list(self):
        response = self.owner.post('/lists', json={'name': 'Group'})
        self.assertEqual(response.status_code, 201)
        return response.get_json()['id']

    def create_task(self, client, title, list_id=None, user_id=None):
        data = {
            'title': title,
            'due_datetime': None,
            'priority': 'High',
            'tag': 'School',
        }
        if list_id is not None:
            data['list_id'] = list_id
        if user_id is not None:
            data['user_id'] = user_id
        response = client.post('/tasks', json=data)
        return response

    def add_member(self):
        response = self.owner.post(
            f'/lists/{self.list_id}/members',
            json={'username': 'member'},
        )
        self.assertEqual(response.status_code, 201)

    def test_personal_tasks_are_scoped_and_owner_comes_from_session(self):
        owner_create = self.create_task(self.owner, 'Owner personal', user_id=2)
        member_create = self.create_task(self.member, 'Member personal', user_id=1)
        self.assertEqual(owner_create.status_code, 201)
        self.assertEqual(member_create.status_code, 201)

        owner_tasks = self.owner.get('/tasks').get_json()
        member_tasks = self.member.get('/tasks').get_json()
        self.assertEqual([task['title'] for task in owner_tasks], ['Owner personal'])
        self.assertEqual(owner_tasks[0]['user_id'], 1)
        self.assertIsNone(owner_tasks[0]['list_id'])
        self.assertEqual([task['title'] for task in member_tasks], ['Member personal'])
        self.assertEqual(member_tasks[0]['user_id'], 2)

    def test_shared_tasks_require_membership_to_read_and_create(self):
        denied_create = self.create_task(
            self.member, 'Denied before invitation', list_id=self.list_id
        )
        self.assertEqual(denied_create.status_code, 404)

        self.add_member()
        owner_create = self.create_task(self.owner, 'Owner shared', list_id=self.list_id)
        member_create = self.create_task(self.member, 'Member shared', list_id=self.list_id)
        self.assertEqual(owner_create.status_code, 201)
        self.assertEqual(member_create.status_code, 201)

        owner_tasks = self.owner.get(f'/tasks?list_id={self.list_id}').get_json()
        member_tasks = self.member.get(f'/tasks?list_id={self.list_id}').get_json()
        self.assertEqual(
            [task['title'] for task in owner_tasks],
            ['Owner shared', 'Member shared'],
        )
        self.assertEqual(
            [task['user_id'] for task in owner_tasks],
            [1, 2],
        )
        self.assertEqual(
            [task['title'] for task in member_tasks],
            ['Owner shared', 'Member shared'],
        )
        self.assertEqual(
            self.outsider.get(f'/tasks?list_id={self.list_id}').status_code,
            404,
        )
        self.assertEqual(self.outsider.get('/tasks?list_id=not-an-id').status_code, 400)
        self.assertEqual(
            self.owner.post('/tasks', json={
                'title': 'Invalid list identifier',
                'due_datetime': None,
                'priority': 'Low',
                'tag': 'School',
                'list_id': 1.5,
            }).status_code,
            400,
        )

    def test_shared_members_can_update_and_delete_but_outsiders_cannot(self):
        self.add_member()
        created = self.create_task(
            self.owner, 'Shared task', list_id=self.list_id
        )
        task_id = created.get_json()['id']
        updates = {
            'title': 'Updated by member',
            'due_datetime': None,
            'priority': 'Low',
            'tag': 'Personal',
        }

        outsider_update = self.outsider.put(f'/tasks/{task_id}', json=updates)
        self.assertEqual(outsider_update.status_code, 404)
        self.assertEqual(
            self.member.put(f'/tasks/{task_id}', json=updates).status_code,
            200,
        )
        with closing(self.connect_db()) as conn:
            self.assertEqual(
                conn.execute(
                    'SELECT title FROM tasks WHERE id = ?',
                    (task_id,),
                ).fetchone()['title'],
                'Updated by member',
            )

        self.assertEqual(self.outsider.delete(f'/tasks/{task_id}').status_code, 404)
        self.assertEqual(self.member.delete(f'/tasks/{task_id}').status_code, 200)
        self.assertEqual(
            self.owner.get(f'/tasks?list_id={self.list_id}').get_json(),
            [],
        )

    def test_personal_task_update_and_delete_are_owner_only(self):
        task_id = self.create_task(self.owner, 'Private task').get_json()['id']
        updates = {
            'title': 'Attempted update',
            'due_datetime': None,
            'priority': 'Low',
            'tag': 'Personal',
        }

        self.assertEqual(self.member.put(f'/tasks/{task_id}', json=updates).status_code, 404)
        self.assertEqual(self.member.delete(f'/tasks/{task_id}').status_code, 404)
        self.assertEqual(self.owner.put(f'/tasks/{task_id}', json=updates).status_code, 200)
        self.assertEqual(self.owner.delete(f'/tasks/{task_id}').status_code, 200)

    def test_inaccessible_or_missing_task_mutations_return_not_found(self):
        updates = {
            'title': 'Not found',
            'due_datetime': None,
            'priority': 'Low',
            'tag': 'Personal',
        }
        self.assertEqual(self.owner.put('/tasks/999', json=updates).status_code, 404)
        self.assertEqual(self.owner.delete('/tasks/999').status_code, 404)
        self.assertEqual(self.owner.post('/tasks', json={
            'title': 'Invalid shared list',
            'due_datetime': None,
            'priority': 'Low',
            'tag': 'School',
            'list_id': 999,
        }).status_code, 404)


if __name__ == '__main__':
    unittest.main()
