import sqlite3
from datetime import datetime

DB_PATH = "aven_memory.db"

def init_db():
    """Initializes SQLite tables for message logs and long-term key-value memory."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Store chat history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Store user preferences and key facts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_facts (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def save_chat_message(role: str, content: str):
    """Persists a single message into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversation_logs (role, content) VALUES (?, ?)",
        (role, content)
    )
    conn.commit()
    conn.close()

def load_recent_history(limit: int = 10):
    """Fetches recent conversation history for prompt context initialization."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM conversation_logs ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    # Return chronologically ordered messages
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def store_fact(key: str, value: str):
    """Stores or updates a specific user fact or preference."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_facts (key, value, updated_at) 
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
    """, (key, value))
    conn.commit()
    conn.close()

def get_all_facts():
    """Retrieves all stored long-term facts as a string summary for system prompt insertion."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM user_facts")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return ""
    
    return "\n".join([f"- {row[0]}: {row[1]}" for row in rows])

if __name__ == "__main__":
    init_db()
    print("[MEMORY] SQLite Database initialized successfully.")