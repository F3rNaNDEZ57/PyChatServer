const socket = io();

socket.on('connect', () => {
    console.log('Connected to server');
    socket.emit('join', { username: username });
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    socket.emit('leave', { username: username });
});

socket.on('message', (data) => {
    const li = document.createElement('li');
    li.textContent = `${data.sender}: ${data.message}`;
    document.getElementById('chat').appendChild(li);
});

socket.on('update_user_list', (data) => {
    const userElement = document.getElementById(`user-${data.sender}`);
    if (userElement) {
        userElement.querySelector('small').textContent = `Last message: ${data.message}`;
    } else {
        const userList = document.getElementById('user-list');
        const li = document.createElement('li');
        li.id = `user-${data.sender}`;
        li.innerHTML = `
            <div>
                <strong>${data.sender}</strong><br>
                <small>Last message: ${data.message}</small><br>
                <button onclick="window.location.href='${window.location.origin}/chat/${data.sender}'">Chat</button>
            </div>
        `;
        userList.appendChild(li);
    }
});

socket.on('update_group_list', (data) => {
    const groupElement = document.getElementById(`group-${data.group_id}`);
    if (groupElement) {
        groupElement.querySelector('small').textContent = `Last message: ${data.message}`;
    } else {
        const groupList = document.getElementById('group-list');
        const li = document.createElement('li');
        li.id = `group-${data.group_id}`;
        li.innerHTML = `
            <div>
                <strong>${data.group_name}</strong><br>
                <small>Last message: ${data.message}</small><br>
                <button onclick="window.location.href='${window.location.origin}/group_chat/${data.group_id}'">Chat</button>
            </div>
        `;
        groupList.appendChild(li);
    }
});

socket.on('new_group', (data) => {
    const groupList = document.getElementById('group-list');
    const li = document.createElement('li');
    li.id = `group-${data.group_id}`;
    li.innerHTML = `
        <div>
            <strong>${data.group_name}</strong><br>
            <small>Last message: ${data.last_message}</small><br>
            <button onclick="window.location.href='${window.location.origin}/group_chat/${data.group_id}'">Chat</button>
        </div>
    `;
    groupList.appendChild(li);
});

function searchUsers() {
    const query = document.getElementById('search').value;
    if (query.trim() === '') {
        document.getElementById('search-results').innerHTML = '';
        return;
    }
    fetch(`/search_users?query=${query}`)
        .then(response => response.json())
        .then(users => {
            const userList = document.getElementById('search-results');
            userList.innerHTML = '';
            users.forEach(user => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div>
                        <strong>${user.username}</strong><br>
                        <button onclick="window.location.href='${window.location.origin}/chat/${user.username}'">Chat</button>
                    </div>
                `;
                userList.appendChild(li);
            });
        });
}
