const taskForm = document.getElementById('task-form');
const taskList = document.getElementById('task-list');

function renderTasks(tasks) {
    taskList.innerHTML = ''; // clear before re-rendering

    tasks.forEach(task => {
        const li = document.createElement('li');
        li.className = `task priority-${task.priority.toLowerCase()} ${task.done ? 'done' : ''}`;
        li.dataset.id = task.id;

        li.innerHTML = `
            <input type="checkbox" ${task.done ? 'checked' : ''}>
            <span class="task-title">${task.title}</span>
            <span class="task-due">${task.due_datetime}</span>
            <span class="task-tag">${task.tag}</span>
            <button class="edit-btn">Edit</button>
            <button class="delete-btn">Delete</button>
        `;

        taskList.appendChild(li);
    });
}

async function loadTasks() {
    const response = await fetch('/tasks');
    const tasks = await response.json();
    renderTasks(tasks);
}

document.addEventListener('DOMContentLoaded', loadTasks);

taskForm.addEventListener('submit', async (e) => {
    e.preventDefault(); // stop the page from reloading

    const newTask = {
        title: document.getElementById('title').value,
        due_datetime: document.getElementById('due_datetime').value,
        priority: document.getElementById('priority').value,
        tag: document.getElementById('tag').value
    };

    await fetch('/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTask)
    });

    taskForm.reset();  // clear the form fields
    loadTasks();       // re-fetch and re-render so the new task shows up
});

taskList.addEventListener('click', async (e) => {
    if (e.target.classList.contains('delete-btn')) {
        const li = e.target.closest('.task');
        const taskId = li.dataset.id;

        if (confirm('Delete this task?')) {
            await fetch(`/tasks/${taskId}`, { method: 'DELETE' });
            loadTasks();
        }
    }
});