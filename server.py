from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from forms import RegistrationForm, LoginForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def get_db_connection():
    conn = sqlite3.connect('chat.db')
    conn.row_factory = sqlite3.Row
    return conn

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return User(id=user['id'], username=user['username'], password=user['password'])
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (form.username.data, hashed_password))
        conn.commit()
        conn.close()
        flash('You have successfully registered! You can now login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (form.username.data,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], form.password.data):
            user_obj = User(id=user['id'], username=user['username'], password=user['password'])
            login_user(user_obj)
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT u.id, u.username, MAX(m.timestamp) as last_message_time, m.message as last_message
    FROM users u
    LEFT JOIN messages m ON (u.id = m.sender_id AND m.recipient_id = ?) OR (u.id = m.recipient_id AND m.sender_id = ?)
    WHERE u.id != ?
    GROUP BY u.id
    HAVING MAX(m.timestamp) IS NOT NULL
    ORDER BY last_message_time DESC
    ''', (current_user.id, current_user.id, current_user.id))
    users = cursor.fetchall()

    cursor.execute('''
    SELECT g.id, g.name, MAX(m.timestamp) as last_message_time, m.message as last_message
    FROM groups g
    JOIN group_members gm ON gm.group_id = g.id
    LEFT JOIN group_messages m ON m.group_id = g.id
    WHERE gm.user_id = ?
    GROUP BY g.id, g.name
    ORDER BY last_message_time DESC
    ''', (current_user.id,))
    groups = cursor.fetchall()
    conn.close()

    return render_template('index.html', username=current_user.username, users=users, groups=groups)

@app.route('/search_users', methods=['GET'])
@login_required
def search_users():
    search_query = request.args.get('query')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE username LIKE ? AND id != ?", (f'%{search_query}%', current_user.id))
    users = cursor.fetchall()
    conn.close()
    return jsonify([{"id": user["id"], "username": user["username"]} for user in users])

@app.route('/chat/<recipient_username>', methods=['GET'])
@login_required
def chat(recipient_username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (recipient_username,))
    recipient = cursor.fetchone()
    conn.close()
    if recipient:
        return render_template('chat.html', username=current_user.username, recipient_username=recipient_username)
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('index'))

@app.route('/chat_history/<recipient_username>', methods=['GET'])
@login_required
def chat_history(recipient_username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (recipient_username,))
    recipient = cursor.fetchone()
    if recipient:
        cursor.execute('''
        SELECT sender_id, recipient_id, message, timestamp
        FROM messages
        WHERE (sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?)
        ORDER BY timestamp ASC
        ''', (current_user.id, recipient['id'], recipient['id'], current_user.id))
        messages = cursor.fetchall()
        conn.close()
        messages = [
            {"sender_id": msg["sender_id"], "recipient_id": msg["recipient_id"], "message": msg["message"], "timestamp": msg["timestamp"]}
            for msg in messages
        ]
        return jsonify(messages)
    return jsonify([])

@app.route('/create_group', methods=['POST'])
@login_required
def create_group():
    group_name = request.form.get('group_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO groups (name, creator_id) VALUES (?, ?)", (group_name, current_user.id))
    group_id = cursor.lastrowid
    cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (group_id, current_user.id))
    conn.commit()
    conn.close()
    
    # Emit event to notify all users about the new group
    socketio.emit('new_group', {'group_id': group_id, 'group_name': group_name, 'last_message': 'No messages yet'})
    
    return redirect(url_for('index'))

@app.route('/add_group_member', methods=['POST'])
@login_required
def add_group_member():
    group_id = request.form.get('group_id')
    username = request.form.get('username')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user:
        cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (group_id, user['id']))
        conn.commit()
    conn.close()
    return redirect(url_for('group_chat', group_id=group_id))

@app.route('/group_chat/<int:group_id>', methods=['GET'])
@login_required
def group_chat(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
    group = cursor.fetchone()
    conn.close()
    if group:
        return render_template('group_chat.html', username=current_user.username, group_name=group['name'], group_id=group_id)
    else:
        flash('Group not found.', 'danger')
        return redirect(url_for('index'))

@app.route('/group_chat_history/<int:group_id>', methods=['GET'])
@login_required
def group_chat_history(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT sender_id, message, timestamp
    FROM group_messages
    WHERE group_id = ?
    ORDER BY timestamp ASC
    ''', (group_id,))
    messages = cursor.fetchall()
    conn.close()
    messages = [
        {"sender_id": msg["sender_id"], "message": msg["message"], "timestamp": msg["timestamp"]}
        for msg in messages
    ]
    return jsonify(messages)

@socketio.on('join')
def handle_join(data):
    room = data['username']
    join_room(room)

@socketio.on('leave')
def handle_leave(data):
    room = data['username']
    leave_room(room)

@socketio.on('message')
def handle_message(data):
    recipient_username = data['recipient']
    message = data['message']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (recipient_username,))
    recipient = cursor.fetchone()
    
    if recipient:
        cursor.execute("INSERT INTO messages (sender_id, recipient_id, message) VALUES (?, ?, ?)",
                       (current_user.id, recipient['id'], message))
        conn.commit()
        conn.close()
        emit('message', {'sender': current_user.username, 'message': message}, room=recipient_username)
        emit('message', {'sender': current_user.username, 'message': message}, room=current_user.username)
        # Notify index.html to update
        emit('update_user_list', {'sender': current_user.username, 'message': message, 'recipient': recipient_username}, broadcast=True)
    else:
        emit('message', {'sender': 'System', 'message': 'Recipient not found.'}, room=current_user.username)

@socketio.on('join_group')
def handle_join_group(data):
    join_room(data['group_id'])

@socketio.on('leave_group')
def handle_leave_group(data):
    leave_room(data['group_id'])

@socketio.on('group_message')
def handle_group_message(data):
    group_id = data['group_id']
    message = data['message']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO group_messages (group_id, sender_id, message) VALUES (?, ?, ?)",
                   (group_id, current_user.id, message))
    conn.commit()
    conn.close()
    emit('group_message', {'sender': current_user.username, 'message': message}, room=group_id)
    # Notify index.html to update
    emit('update_group_list', {'group_id': group_id, 'message': message}, broadcast=True)

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(current_user.username)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(current_user.username)

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
