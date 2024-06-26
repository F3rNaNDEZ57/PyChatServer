# server.py
from flask import Flask, render_template, redirect, url_for, flash, request
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
    return render_template('index.html', username=current_user.username)

@socketio.on('join')
def handle_join(data):
    room = data['username']
    join_room(room)
    emit('message', {'sender': 'System', 'message': f'{data["username"]} has joined the chat'}, room=room)

@socketio.on('leave')
def handle_leave(data):
    room = data['username']
    leave_room(room)
    emit('message', {'sender': 'System', 'message': f'{data["username"]} has left the chat'}, room=room)

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
    else:
        emit('message', {'sender': 'System', 'message': 'Recipient not found.'}, room=current_user.username)

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(current_user.username)
        emit('message', {'sender': 'System', 'message': f'{current_user.username} has joined the chat'}, room=current_user.username)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(current_user.username)
        emit('message', {'sender': 'System', 'message': f'{current_user.username} has left the chat'}, room=current_user.username)

if __name__ == '__main__':
    socketio.run(app, debug=True)
