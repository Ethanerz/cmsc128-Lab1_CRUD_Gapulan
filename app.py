import sqlite3
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('todo.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tasks', methods=['GET'])
def get_tasks():
    conn = get_db()
    tasks = conn.execute('SELECT * FROM tasks').fetchall()
    conn.close()
    return jsonify([dict(row) for row in tasks])
    
@app.route('/tasks', methods=['POST'])
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
def delete_task(task_id):
    conn = get_db()
    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Task deleted'})

if __name__ == '__main__':
    app.run(debug=True)