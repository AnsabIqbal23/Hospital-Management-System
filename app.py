import streamlit as st
from db import init_db, get_connection
from auth import login, require_role
from anonymization import mask_name, mask_contact
from logs import log_action
from datetime import datetime
import pandas as pd

# Initialize database
init_db()


# Login Page
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


if not st.session_state.logged_in:
    st.title("🏥 Hospital Management System")
    st.subheader("Login")


    username = st.text_input("Username")
    password = st.text_input("Password", type="password")


    if st.button("Login"):
        user = login(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.user_id = user["user_id"]
            st.session_state.role = user["role"]
            log_action(user["user_id"], user["role"], "LOGIN", "User logged in")
            st.rerun()
        else:
            st.error("Invalid Credentials")
    st.stop()


# Dashboard
st.title("🏥 Hospital Dashboard")
st.write(f"Logged in as: **{st.session_state.role.upper()}**")

if st.sidebar.button("Logout"):
    log_action(st.session_state.user_id, st.session_state.role, "LOGOUT", "User logged out")
    st.session_state.logged_in = False
    st.rerun()

menu = ["Add Patient", "View Patients", "Audit Logs"]
choice = st.sidebar.selectbox("Menu", menu)


# --------------------- Add Patient (Receptionist/Admin) ---------------------
if choice == "Add Patient":
    require_role(["admin", "receptionist"])


    name = st.text_input("Name")
    contact = st.text_input("Contact")
    diagnosis = st.text_input("Diagnosis")


    if st.button("Save"):
        anon_name = mask_name(name)
        anon_contact = mask_contact(contact)
        date_added = datetime.now().strftime("%Y-%m-%d")


        conn = get_connection()
        c = conn.cursor()


        c.execute("INSERT INTO patients (name, contact, diagnosis, anonymized_name, anonymized_contact, date_added) VALUES (?, ?, ?, ?, ?, ?)",
        (name, contact, diagnosis, anon_name, anon_contact, date_added))


        conn.commit()
        conn.close()


        log_action(st.session_state.user_id, st.session_state.role, "ADD_PATIENT", name)


        st.success("Patient added successfully!")


# --------------------- View Patients (Role-Based View) ---------------------
if choice == "View Patients":
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM patients", conn)
    conn.close()


    role = st.session_state.role


    if role == "doctor":
        st.dataframe(df[["patient_id", "anonymized_name", "anonymized_contact", "diagnosis", "date_added"]])


    elif role == "receptionist":
        st.dataframe(df[["patient_id", "anonymized_name", "anonymized_contact", "date_added"]])


    else: # admin
        st.dataframe(df)


# --------------------- Audit Logs (Admin Only) ---------------------
if choice == "Audit Logs":
    require_role(["admin"])


    conn = get_connection()
    logs = pd.read_sql_query("SELECT * FROM logs", conn)
    conn.close()


    st.dataframe(logs)