import sqlite3
import config

def init_db():
    conn = sqlite3.connect(config.DATABASE_URL)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
                  status TEXT, join_date TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect(config.DATABASE_URL)
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO users
                 (user_id, username, first_name, status, join_date)
                 VALUES (?, ?, ?, 'pending', datetime('now'))""",
              (user_id, username, first_name))
    conn.commit()
    is_new = c.rowcount > 0
    conn.close()
    return is_new

def get_user_status(user_id):
    conn = sqlite3.connect(config.DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def update_user_status(user_id, status):
    conn = sqlite3.connect(config.DATABASE_URL)
    c = conn.cursor()
    c.execute("UPDATE users SET status=? WHERE user_id=?", (status, user_id))
    conn.commit()
    conn.close()

def get_all_approved_users():
    conn = sqlite3.connect(config.DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE status='approved'")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_stats():
    conn = sqlite3.connect(config.DATABASE_URL)
    c = conn.cursor()
    stats = {}
    for status in ['approved', 'pending', 'rejected']:
        c.execute("SELECT COUNT(*) FROM users WHERE status=?", (status,))
        stats[status] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users")
    stats['total'] = c.fetchone()[0]
    conn.close()
    return stats

def get_users_paginated(page=1, per_page=5):
    conn = sqlite3.connect(config.DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page
    
    c.execute("SELECT user_id, username, first_name, status FROM users LIMIT ? OFFSET ?", (per_page, offset))
    rows = c.fetchall()
    conn.close()
    return rows, total_pages, page