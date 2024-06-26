// static/js/chat_scripts.js

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
    if (data.sender !== 'System') {
        const li = document.createElement('li');
        li.textContent = `${data.sender}: ${data.message}`;
        document.getElementById('chat').appendChild(li);
    }
});

document.addEventListener('DOMContentLoaded', (event) => {
    fetch(`/chat_history/${recipientUsername}`)
        .then(response => response.json())
        .then(messages => {
            const chatList = document.getElementById('chat');
            chatList.innerHTML = '';
            const currentUserId = currentUser.id;
            const currentUsername = currentUser.username;
            messages.forEach(msg => {
                const sender = msg.sender_id === currentUserId ? currentUsername : recipientUsername;
                const li = document.createElement('li');
                li.textContent = `${sender}: ${msg.message}`;
                chatList.appendChild(li);
            });
        });
});

function sendMessage() {
    const recipient = document.getElementById('recipient').value;
    const message = document.getElementById('message').value;
    socket.emit('message', { recipient, message });
    document.getElementById('message').value = '';
}
