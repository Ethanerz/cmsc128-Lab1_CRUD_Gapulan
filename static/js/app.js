const taskForm = document.getElementById('task-form');
const taskList = document.getElementById('task-list');
const taskError = document.getElementById('task-error');

function showTaskError(message) {
    taskError.textContent = message;
    taskError.hidden = false;
}

function clearTaskError() {
    taskError.textContent = '';
    taskError.hidden = true;
}

async function checkResponse(response) {
    if (!response.ok) {
        let message = `Request failed (${response.status})`;
        try {
            const body = await response.json();
            message = body.error || body.message || message;
        } catch (error) {
            if (!(error instanceof SyntaxError)) {
                throw error;
            }
        }
        throw new Error(message);
    }

    return response;
}

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
    try {
        const response = await checkResponse(await fetch('/tasks'));
        const tasks = await response.json();
        renderTasks(tasks);
        clearTaskError();
    } catch (error) {
        showTaskError(`Unable to load tasks: ${error.message}`);
    }
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

    try {
        await checkResponse(await fetch('/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newTask)
        }));

        taskForm.reset();
        await loadTasks();
    } catch (error) {
        showTaskError(`Unable to create task: ${error.message}`);
    }
});

taskList.addEventListener('click', async (e) => {
    if (e.target.classList.contains('delete-btn')) {
        const li = e.target.closest('.task');
        const taskId = li.dataset.id;

        if (confirm('Delete this task?')) {
            try {
                await checkResponse(await fetch(`/tasks/${taskId}`, { method: 'DELETE' }));
                await loadTasks();
            } catch (error) {
                showTaskError(`Unable to delete task: ${error.message}`);
            }
        }
    }

    if (e.target.classList.contains('save-btn')) {
        const li = e.target.closest('.task');
        const taskId = li.dataset.id;

        const updatedTask = {
            title: li.querySelector('.edit-title').value,
            due_datetime: li.querySelector('.edit-due').value,
            priority: li.querySelector('.edit-priority').value,
            tag: li.querySelector('.edit-tag').value
        };

        try {
            await checkResponse(await fetch(`/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatedTask)
            }));
            await loadTasks();
        } catch (error) {
            showTaskError(`Unable to update task: ${error.message}`);
        }
    }
	if (e.target.classList.contains('edit-btn')) {
    const li = e.target.closest('.task');
    const title = li.querySelector('.task-title').textContent;
    const due = li.querySelector('.task-due').textContent;
    const tag = li.querySelector('.task-tag').textContent;

    li.innerHTML = `
        <input type="text" class="edit-title" value="${title}">
        <input type="datetime-local" class="edit-due" value="${due}">
        <select class="edit-priority">
            <option value="Low">Low</option>
            <option value="Med">Med</option>
            <option value="High">High</option>
        </select>
        <select class="edit-tag">
            <option value="School">School</option>
            <option value="Personal">Personal</option>
            <option value="Others">Others</option>
        </select>
        <button class="save-btn">Save</button>
    `;
}
});
