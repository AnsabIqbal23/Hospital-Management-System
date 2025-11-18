from db import get_connection
from datetime import datetime

def log_action(user_id, role, action, details):
    conn = get_connection()
    c = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("INSERT INTO logs (user_id, role, action, timestamp, details) VALUES (?, ?, ?, ?, ?)",
            (user_id, role, action, timestamp, details))


    conn.commit()
    conn.close()