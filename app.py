import os
import sqlite3
from datetime import timedelta
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, flash, request, jsonify, render_template, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    raise RuntimeError('SECRET_KEY must be set in the .env file.')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

def get_db():
    conn = sqlite3.connect('todo.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required.'}), 401
        return view(*args, **kwargs)
    return wrapped_view

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/tasks', methods=['GET'])
@login_required
def get_tasks():
    conn = get_db()
    tasks = conn.execute('SELECT * FROM tasks').fetchall()
    conn.close()
    return jsonify([dict(row) for row in tasks])
    
@app.route('/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.get_json()
    conn = get_db()
    conn.execute('''
        INSERT INTO tasks (title, due_datetime, priority, tag, done)
        VALUES (?, ?, ?, ?, 0)
    ''', (data['title'], data['due_datetime'], data['priority'], data['tag']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Task created'}), 201
    
@app.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    data = request.get_json()
    conn = get_db()
    conn.execute('''
        UPDATE tasks
        SET title = ?, due_datetime = ?, priority = ?, tag = ?
        WHERE id = ?
    ''', (data['title'], data['due_datetime'], data['priority'], data['tag'], task_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Task updated'})

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    conn = get_db()
    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Task deleted'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        display_name = request.form.get('display_name', '').strip()
        password = request.form.get('password', '')

        if not username or not display_name or not password:
            return render_template(
                'register.html',
                error='All fields are required.',
                username=username,
                display_name=display_name
            )

        password_hash = generate_password_hash(password)

        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO users (username, display_name, password_hash)
                VALUES (?, ?, ?)
            ''', (username, display_name, password_hash))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            return render_template(
                'register.html',
                error='That username is already taken.',
                username=username,
                display_name=display_name
            )
        finally:
            conn.close()

        flash('Your account was created. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('login.html', error='Username and password are required.')

        conn = get_db()
        user = conn.execute(
            'SELECT id, display_name, password_hash FROM users WHERE username = ?',
            (username,)
        ).fetchone()
        conn.close()

        if user is None or not check_password_hash(user['password_hash'], password):
            return render_template('login.html', error='Invalid username or password.')

        session.clear()
        session.permanent = True
        session['user_id'] = user['id']
        session['display_name'] = user['display_name']
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)