from datetime import datetime, timezone
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "aven_central.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite database tables for chat logs and long-term memory."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default_user',
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_str TEXT DEFAULT (date('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS long_term_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT UNIQUE NOT NULL,
            category TEXT DEFAULT 'general',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database schema initialized: {os.path.basename(DB_PATH)}")


def log_chat(sender: str, message: str, user_id: str = "default_user"):
    """Logs incoming and outgoing messages with dynamic schema resolution."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(chat_logs)")
        cols_info = cursor.fetchall()

        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")

        fields = []
        values = []

        for col in cols_info:
            col_name = col["name"]
            is_pk = col["pk"]
            not_null = col["notnull"]
            default_val = col["dflt_value"]

            if is_pk and col_name.lower() == "id":
                continue

            if col_name == "sender":
                fields.append("sender")
                values.append(sender)
            elif col_name == "message":
                fields.append("message")
                values.append(message)
            elif col_name == "user_id":
                fields.append("user_id")
                values.append(user_id)
            elif col_name == "timestamp":
                fields.append("timestamp")
                values.append(now_str)
            elif col_name == "date_str":
                fields.append("date_str")
                values.append(date_str)
            elif not_null and default_val is None:
                fields.append(col_name)
                col_type = col["type"].upper() if col["type"] else "TEXT"
                if "INT" in col_type:
                    values.append(0)
                elif "REAL" in col_type or "FLOAT" in col_type:
                    values.append(0.0)
                else:
                    values.append("")

        placeholders = ", ".join(["?"] * len(fields))
        field_names = ", ".join(fields)

        query = f"INSERT INTO chat_logs ({field_names}) VALUES ({placeholders})"
        cursor.execute(query, values)
        conn.commit()
    finally:
        conn.close()


def get_chat_history(limit: int = 6) -> list:
    """Fetches the most recent chat history items in chronological order."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sender, message FROM chat_logs ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"sender": row["sender"], "message": row["message"]}
        for row in reversed(rows)
    ]


def get_all_memories() -> list:
    """Retrieves all stored long-term memory facts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT fact, category FROM long_term_memories ORDER BY id ASC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"fact": row["fact"], "category": row["category"]} for row in rows]


get_long_term_memories = get_all_memories


def save_memory(fact: str, category: str = "general"):
    """Inserts a new unique long-term memory fact."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO long_term_memories (fact, category) VALUES"
            " (?, ?)",
            (fact, category),
        )
        conn.commit()
    finally:
        conn.close()


add_long_term_memory = save_memory