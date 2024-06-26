import sqlite3

def setup_db():
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    
    # Drop the existing tables if they exist
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS messages')
    cursor.execute('DROP TABLE IF EXISTS groups')
    cursor.execute('DROP TABLE IF EXISTS group_members')
    cursor.execute('DROP TABLE IF EXISTS group_messages')
    
    # Create tables
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY,
        sender_id INTEGER,
        recipient_id INTEGER,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(sender_id) REFERENCES users(id),
        FOREIGN KEY(recipient_id) REFERENCES users(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        creator_id INTEGER NOT NULL,
        FOREIGN KEY (creator_id) REFERENCES users(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE group_members (
        group_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (group_id) REFERENCES groups(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE group_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES groups(id),
        FOREIGN KEY (sender_id) REFERENCES users(id)
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_db()
