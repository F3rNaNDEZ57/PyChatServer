# db_setup.py
import sqlite3

def setup_db():
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    
    # Drop the existing tables if they exist
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS messages')
    
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
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_db()
