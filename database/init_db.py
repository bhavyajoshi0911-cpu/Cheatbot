import sqlite3
from pathlib import Path

from config import Config


DB_PATH = Config.DATABASE


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT DEFAULT '📁',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            category_id INTEGER,
            icon TEXT DEFAULT '🔗',
            open_type TEXT DEFAULT 'website',
            executable_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, resource_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(resource_id) REFERENCES resources(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS launch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            launched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(resource_id) REFERENCES resources(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shortcuts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            shortcut TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, resource_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(resource_id) REFERENCES resources(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_name ON resources(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_launch_history_user ON launch_history(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)')

    seed_categories(cursor)
    cleanup_duplicate_resources(cursor)
    seed_resources(cursor)
    cleanup_duplicate_resources(cursor)
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_resources_name ON resources(name)')
    conn.commit()
    conn.close()


def seed_categories(cursor):
    categories = [
        ('Development', '💻'),
        ('Productivity', '⚡'),
        ('Learning', '📚'),
        ('Communication', '💬'),
        ('Design', '🎨'),
        ('Entertainment', '🎬'),
    ]

    for name, icon in categories:
        cursor.execute(
            'INSERT OR IGNORE INTO categories (name, icon) VALUES (?, ?)',
            (name, icon)
        )


def seed_resources(cursor):
    resources = [
        ('VS Code', 'https://code.visualstudio.com/', 'Code editor for development work', 1, '💻', 'local', r'C:\Users\DELL\AppData\Local\Programs\Microsoft VS Code\Code.exe'),
        ('GitHub', 'https://github.com/', 'Code hosting and collaboration platform', 1, '🐙', 'website', None),
        ('GitLab', 'https://gitlab.com/', 'Git platform for source control', 1, '🦊', 'website', None),
        ('Stack Overflow', 'https://stackoverflow.com/', 'Q&A for developers', 1, '💡', 'website', None),
        ('Postman', 'https://www.postman.com/', 'API testing and collaboration', 1, '📬', 'website', None),
        ('Jupyter', 'https://jupyter.org/', 'Interactive notebooks for data science', 1, '🧪', 'website', None),
        ('Java Cheat Sheet', 'https://www.w3schools.com/java/', 'Core Java syntax, OOP basics, loops, classes, and collections', 3, '☕', 'website', None),
        ('YouTube', 'https://www.youtube.com/', 'Video tutorials and learning', 3, '▶️', 'website', None),
        ('Coursera', 'https://www.coursera.org/', 'Online learning platform', 3, '🎓', 'website', None),
        ('Udemy', 'https://www.udemy.com/', 'Courses for software and business skills', 3, '📘', 'website', None),
        ('LeetCode', 'https://leetcode.com/', 'Coding practice and interview prep', 3, '🧠', 'website', None),
        ('W3Schools', 'https://www.w3schools.com/', 'Web dev documentation and tutorials', 3, '🌐', 'website', None),
        ('Google', 'https://www.google.com/', 'Search the web', 2, '🔎', 'website', None),
        ('Gmail', 'https://mail.google.com/', 'Email and communication', 2, '📧', 'website', None),
        ('Google Drive', 'https://drive.google.com/', 'File storage and docs', 2, '📁', 'website', None),
        ('Notion', 'https://www.notion.so/', 'Notes and productivity workspace', 2, '📝', 'website', None),
        ('WhatsApp Web', 'https://web.whatsapp.com/', 'Messaging and team chat', 4, '💬', 'website', None),
        ('Slack', 'https://slack.com/', 'Team communication tool', 4, '💼', 'website', None),
        ('Microsoft Teams', 'https://www.microsoft.com/en-us/microsoft-teams/group-chat-software', 'Meetings and collaboration', 4, '🗂️', 'website', None),
        ('Figma', 'https://www.figma.com/', 'Design and prototyping platform', 5, '🎨', 'website', None),
        ('Canva', 'https://www.canva.com/', 'Design and presentation creation', 5, '🖌️', 'website', None),
        ('ChatGPT', 'https://chat.openai.com/', 'AI assistant for coding and research', 2, '🤖', 'website', None),
    ]

    for item in resources:
        cursor.execute(
            '''
            INSERT OR IGNORE INTO resources (name, url, description, category_id, icon, open_type, executable_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            item
        )


def cleanup_duplicate_resources(cursor):
    rows = cursor.execute('''
        SELECT id, name FROM resources
        WHERE name IN (
            SELECT name FROM resources GROUP BY name HAVING COUNT(*) > 1
        )
        ORDER BY name, id
    ''').fetchall()

    seen = set()
    duplicates = []
    for row in rows:
        if row[1] in seen:
            duplicates.append(row[0])
        else:
            seen.add(row[1])

    for resource_id in duplicates:
        cursor.execute('DELETE FROM resources WHERE id = ?', (resource_id,))

    cursor.execute('DELETE FROM favorites WHERE resource_id NOT IN (SELECT id FROM resources)')
    cursor.execute('DELETE FROM launch_history WHERE resource_id NOT IN (SELECT id FROM resources)')
    cursor.execute('DELETE FROM shortcuts WHERE resource_id NOT IN (SELECT id FROM resources)')
