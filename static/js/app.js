const taskForm = document.getElementById('task-form');
const taskList = document.getElementById('task-list');
const taskError = document.getElementById('task-error');
const listStatus = document.getElementById('list-status');
const listSelector = document.getElementById('list-selector');
const listCreateForm = document.getElementById('list-create-form');
const listInviteForm = document.getElementById('list-invite-form');

function showTaskError(message) {
    taskError.textContent = message;
    taskError.hidden = false;
}

function clearTaskError() {
    taskError.textContent = '';
    taskError.hidden = true;
}

function showListStatus(message) {
    listStatus.textContent = message;
    listStatus.hidden = false;
}

function clearListStatus() {
    listStatus.textContent = '';
    listStatus.hidden = true;
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

function selectedListId() {
    return listSelector.value || null;
}

function updateInviteVisibility() {
    const selectedOption = listSelector.selectedOptions[0];
    const currentUserId = Number(listSelector.dataset.currentUserId);
    listInviteForm.hidden = !selectedOption
        || !selectedOption.value
        || Number(selectedOption.dataset.ownerId) !== currentUserId;
}

function renderTasks(tasks) {
    taskList.replaceChildren();

    tasks.forEach(task => {
        const li = document.createElement('li');
        li.className = `task priority-${task.priority.toLowerCase()} ${task.done ? 'done' : ''}`;
        li.dataset.id = task.id;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = Boolean(task.done);

        const title = document.createElement('span');
        title.className = 'task-title';
        title.textContent = task.title;

        const due = document.createElement('span');
        due.className = 'task-due';
        due.textContent = task.due_datetime || '';

        const tag = document.createElement('span');
        tag.className = 'task-tag';
        tag.textContent = task.tag;

        const editButton = document.createElement('button');
        editButton.type = 'button';
        editButton.className = 'edit-btn';
        editButton.textContent = 'Edit';

        const deleteButton = document.createElement('button');
        deleteButton.type = 'button';
        deleteButton.className = 'delete-btn';
        deleteButton.textContent = 'Delete';

        li.append(checkbox, title, due, tag, editButton, deleteButton);
        taskList.appendChild(li);
    });
}

async function loadLists(preferredListId = selectedListId()) {
    try {
        const response = await checkResponse(await fetch('/lists'));
        const lists = await response.json();

        listSelector.replaceChildren(new Option('Personal tasks', ''));
        lists.forEach(list => {
            const option = new Option(list.name, String(list.id));
            option.dataset.ownerId = String(list.owner_id);
            listSelector.add(option);
        });

        const hasPreferredList = lists.some(
            list => String(list.id) === String(preferredListId)
        );
        listSelector.value = hasPreferredList ? String(preferredListId) : '';
        updateInviteVisibility();
        clearTaskError();
        return true;
    } catch (error) {
        showTaskError(`Unable to load lists: ${error.message}`);
        return false;
    }
}

async function loadTasks() {
    try {
        const listId = selectedListId();
        const query = listId ? `?list_id=${encodeURIComponent(listId)}` : '';
        const response = await checkResponse(await fetch(`/tasks${query}`));
        const tasks = await response.json();
        renderTasks(tasks);
        clearTaskError();
    } catch (error) {
        showTaskError(`Unable to load tasks: ${error.message}`);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    if (await loadLists(null)) {
        await loadTasks();
    }
});

listSelector.addEventListener('change', async () => {
    clearListStatus();
    updateInviteVisibility();
    await loadTasks();
});

listCreateForm.addEventListener('submit', async event => {
    event.preventDefault();
    clearListStatus();

    const name = document.getElementById('list-name').value.trim();
    try {
        const response = await checkResponse(await fetch('/lists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        }));
        const list = await response.json();
        listCreateForm.reset();
        if (!await loadLists(list.id)) {
            return;
        }
        await loadTasks();
        showListStatus(`Created "${list.name}".`);
    } catch (error) {
        showTaskError(`Unable to create list: ${error.message}`);
    }
});

listInviteForm.addEventListener('submit', async event => {
    event.preventDefault();
    clearListStatus();

    const listId = selectedListId();
    const identifier = document.getElementById('list-invite-identifier').value.trim();
    const field = identifier.includes('@') ? 'email' : 'username';
    try {
        const response = await checkResponse(await fetch(`/lists/${listId}/members`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [field]: identifier })
        }));
        const result = await response.json();
        listInviteForm.reset();
        clearTaskError();
        showListStatus(result.message);
    } catch (error) {
        showTaskError(`Unable to invite user: ${error.message}`);
    }
});

taskForm.addEventListener('submit', async event => {
    event.preventDefault();

    const newTask = {
        title: document.getElementById('title').value,
        due_datetime: document.getElementById('due_datetime').value,
        priority: document.getElementById('priority').value,
        tag: document.getElementById('tag').value
    };
    const listId = selectedListId();
    if (listId) {
        newTask.list_id = Number(listId);
    }

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

taskList.addEventListener('click', async event => {
    if (event.target.classList.contains('delete-btn')) {
        const li = event.target.closest('.task');
        if (!confirm('Delete this task?')) {
            return;
        }

        try {
            await checkResponse(await fetch(`/tasks/${li.dataset.id}`, {
                method: 'DELETE'
            }));
            await loadTasks();
        } catch (error) {
            showTaskError(`Unable to delete task: ${error.message}`);
        }
        return;
    }

    if (event.target.classList.contains('save-btn')) {
        const li = event.target.closest('.task');
        const updatedTask = {
            title: li.querySelector('.edit-title').value,
            due_datetime: li.querySelector('.edit-due').value,
            priority: li.querySelector('.edit-priority').value,
            tag: li.querySelector('.edit-tag').value
        };

        try {
            await checkResponse(await fetch(`/tasks/${li.dataset.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatedTask)
            }));
            await loadTasks();
        } catch (error) {
            showTaskError(`Unable to update task: ${error.message}`);
        }
        return;
    }

    if (event.target.classList.contains('edit-btn')) {
        const li = event.target.closest('.task');
        const title = li.querySelector('.task-title').textContent;
        const due = li.querySelector('.task-due').textContent;
        const tag = li.querySelector('.task-tag').textContent;
        const priority = li.className.match(/priority-(low|med|high)/)?.[1] || 'low';

        li.replaceChildren();
        const titleInput = document.createElement('input');
        titleInput.type = 'text';
        titleInput.className = 'edit-title';
        titleInput.value = title;

        const dueInput = document.createElement('input');
        dueInput.type = 'datetime-local';
        dueInput.className = 'edit-due';
        dueInput.value = due;

        const prioritySelect = document.createElement('select');
        prioritySelect.className = 'edit-priority';
        ['Low', 'Med', 'High'].forEach(value => {
            prioritySelect.add(new Option(value, value));
        });
        prioritySelect.value = priority.charAt(0).toUpperCase() + priority.slice(1);

        const tagSelect = document.createElement('select');
        tagSelect.className = 'edit-tag';
        ['School', 'Personal', 'Others'].forEach(value => {
            tagSelect.add(new Option(value, value));
        });
        tagSelect.value = tag;

        const saveButton = document.createElement('button');
        saveButton.type = 'button';
        saveButton.className = 'save-btn';
        saveButton.textContent = 'Save';

        li.append(titleInput, dueInput, prioritySelect, tagSelect, saveButton);
    }
});
