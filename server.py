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

# Database connection
conn = sqlite3.connect('chat.db', check_same_thread=False)
cursor = conn.cursor()

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    cursor.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        return User(id=user[0], username=user[1], password=user[2])
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (form.username.data, hashed_password))
        conn.commit()
        flash('You have successfully registered! You can now login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (form.username.data,))
        user = cursor.fetchone()
        if user and check_password_hash(user[2], form.password.data):
            user_obj = User(id=user[0], username=user[1], password=user[2])
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
    cursor.execute('''
    SELECT u.id, u.username, MAX(m.timestamp), m.message
    FROM users u
    JOIN messages m ON (u.id = m.sender_id AND m.recipient_id = ?) OR (u.id = m.recipient_id AND m.sender_id = ?)
    WHERE u.id != ?
    GROUP BY u.id
    ORDER BY MAX(m.timestamp) DESC
    ''', (current_user.id, current_user.id, current_user.id))
    users = cursor.fetchall()
    return render_template('index.html', username=current_user.username, users=users)


@app.route('/search_users', methods=['GET'])
@login_required
def search_users():
    search_query = request.args.get('query')
    cursor.execute("SELECT id, username FROM users WHERE username LIKE ? AND id != ?", (f'%{search_query}%', current_user.id))
    users = cursor.fetchall()
    return jsonify(users)


@app.route('/chat/<recipient_username>', methods=['GET'])
@login_required
def chat(recipient_username):
    cursor.execute("SELECT id FROM users WHERE username = ?", (recipient_username,))
    recipient = cursor.fetchone()
    if recipient:
        return render_template('chat.html', username=current_user.username, recipient_username=recipient_username)
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('index'))


@app.route('/chat_history/<recipient_username>', methods=['GET'])
@login_required
def chat_history(recipient_username):
    cursor.execute("SELECT id FROM users WHERE username = ?", (recipient_username,))
    recipient = cursor.fetchone()
    if recipient:
        cursor.execute('''
        SELECT sender_id, recipient_id, message, timestamp
        FROM messages
        WHERE (sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?)
        ORDER BY timestamp ASC
        ''', (current_user.id, recipient[0], recipient[0], current_user.id))
        messages = cursor.fetchall()
        messages = [
            {"sender_id": msg[0], "recipient_id": msg[1], "message": msg[2], "timestamp": msg[3]}
            for msg in messages
        ]
        return jsonify(messages)
    return jsonify([])


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
    
    cursor.execute("SELECT id FROM users WHERE username = ?", (recipient_username,))
    recipient = cursor.fetchone()
    
    if recipient:
        cursor.execute("INSERT INTO messages (sender_id, recipient_id, message) VALUES (?, ?, ?)",
                       (current_user.id, recipient[0], message))
        conn.commit()
        emit('message', {'sender': current_user.username, 'message': message}, room=recipient_username)
        emit('message', {'sender': current_user.username, 'message': message}, room=current_user.username)
        # Notify index.html to update
        emit('update_user_list', {'sender': current_user.username, 'message': message, 'recipient': recipient_username}, broadcast=True)
    else:
        emit('message', {'sender': 'System', 'message': 'Recipient not found.'}, room=current_user.username)


@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(current_user.username)


@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(current_user.username)


if __name__ == '__main__':
    socketio.run(app, debug=True)
