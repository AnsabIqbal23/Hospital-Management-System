import streamlit as st
from db import get_connection
from logs import log_action


def login(username, password):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()

    if user:
        return {"user_id": user[0], "username": user[1], "role": user[3]}
    return None

def require_role(allowed_roles):
    role = st.session_state.get("role", None)
    if role not in allowed_roles:
        st.error("Access Denied")
        st.stop()