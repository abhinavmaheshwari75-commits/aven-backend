import sqlite3
from datetime import date

class MemoryEngine:
    def __init__(self, db_path="aven_central.db"):
        self.db_path = db_path

    def get_todays_context(self, user_id: str, limit: int = 10) -> str:
        """Loads long-term facts + recent chat turns for today."""
        today = date.today().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load Long-Term Memories
        cursor.execute(
            "SELECT category, fact_key, fact_value FROM long_term_memories WHERE user_id = ?",
            (user_id,)
        )
        memories = cursor.fetchall()
        mem_str = "\n".join([f"- [{cat}] {k}: {v}" for cat, k, v in memories]) if memories else "None recorded."
        
        # Load Today's Recent Turns
        cursor.execute(
            """SELECT sender, message FROM chat_logs 
               WHERE user_id = ? AND date_stamp = ? 
               ORDER BY timestamp DESC LIMIT ?""",
            (user_id, today, limit)
        )
        logs = cursor.fetchall()[::-1] # Reorder to chronological
        chat_str = "\n".join([f"{sender.capitalize()}: {msg}" for sender, msg in logs]) if logs else "First interaction today."
        
        conn.close()
        
        return f"=== KNOWN USER FACTS ===\n{mem_str}\n\n=== TODAY'S CONVERSATION ({today}) ===\n{chat_str}"

    def log_turn(self, user_id: str, device_type: str, sender: str, message: str):
        """Appends a new turn directly into today's log entry."""
        today = date.today().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO chat_logs (user_id, device_type, date_stamp, sender, message)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, device_type, today, sender, message)
        )
        conn.commit()
        conn.close()