// static/js/scripts.js

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

function searchUsers() {
    const query = document.getElementById('search').value;
    fetch(`/search_users?query=${query}`)
        .then(response => response.json())
        .then(users => {
            const userList = document.getElementById('search-results');
            userList.innerHTML = '';
            users.forEach(user => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div>
                        <strong>${user[1]}</strong><br>
                        <button onclick="window.location.href='${window.location.origin}/chat/${user[1]}'">Chat</button>
                    </div>
                `;
                userList.appendChild(li);
            });
        });
}
