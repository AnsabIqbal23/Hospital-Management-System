import sqlite3

def get_connection():
    return sqlite3.connect("hospital.db", check_same_thread=False)

def init_db():
    try:
        conn = get_connection()
        c = conn.cursor()

        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            role TEXT
        )''')

        # Patients table
        c.execute('''CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            diagnosis TEXT,
            anonymized_name TEXT,
            anonymized_contact TEXT,
            date_added TEXT,
            encrypted_diagnosis TEXT
        )''')

        # Logs table
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            action TEXT,
            timestamp TEXT,
            details TEXT
        )''')

        # Add default users if not exists
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            default_users = [
                ("admin", "admin123", "admin"),
                ("doctor", "doctor123", "doctor"),
                ("receptionist", "recep123", "receptionist")
            ]
            c.executemany("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", default_users)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database initialization error: {str(e)}")