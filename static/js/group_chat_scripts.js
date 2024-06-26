// static/js/group_chat_scripts.js

const socket = io();

socket.on('connect', () => {
    console.log('Connected to server');
    socket.emit('join_group', { group_id: groupId });
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    socket.emit('leave_group', { group_id: groupId });
});

socket.on('group_message', (data) => {
    const li = document.createElement('li');
    li.textContent = `${data.sender}: ${data.message}`;
    document.getElementById('chat').appendChild(li);
});

document.addEventListener('DOMContentLoaded', (event) => {
    fetch(`/group_chat_history/${groupId}`)
        .then(response => response.json())
        .then(messages => {
            const chatList = document.getElementById('chat');
            chatList.innerHTML = '';
            messages.forEach(msg => {
                const li = document.createElement('li');
                li.textContent = `${msg.sender_id}: ${msg.message}`;
                chatList.appendChild(li);
            });
        });
});

function sendGroupMessage() {
    const message = document.getElementById('message').value;
    socket.emit('group_message', { group_id: groupId, message });
    document.getElementById('message').value = '';
}

function searchUsersForGroup() {
    const query = document.getElementById('add-member').value;
    if (query.trim() === '') {
        document.getElementById('add-member-results').innerHTML = '';
        return;
    }
    fetch(`/search_users?query=${query}`)
        .then(response => response.json())
        .then(users => {
            const userList = document.getElementById('add-member-results');
            userList.innerHTML = '';
            users.forEach(user => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div>
                        <strong>${user[1]}</strong><br>
                        <button onclick="addMemberToGroup(${user[0]}, '${user[1]}')">Add</button>
                    </div>
                `;
                userList.appendChild(li);
            });
        });
}

function addMemberToGroup(userId, username) {
    fetch('/add_group_member', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ group_id: groupId, username: username })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`${username} added to the group.`);
            document.getElementById('add-member-results').innerHTML = '';
        } else {
            alert(`Failed to add ${username} to the group.`);
        }
    });
}

document.getElementById('add-member-form').addEventListener('submit', function (event) {
    event.preventDefault();
    const username = document.getElementById('add-member').value;
    addMemberToGroup(null, username); // Pass null for userId as it will be fetched in the function
});
