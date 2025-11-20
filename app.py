import streamlit as st
from db import init_db, get_connection
from auth import login, require_role
from anonymization import mask_name, mask_contact, mask_diagnosis, encrypt_value, decrypt_value
from logs import log_action
from datetime import datetime
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go

# Initialize database and system start time
init_db()

# Track system start time for uptime
if "system_start_time" not in st.session_state:
    st.session_state.system_start_time = time.time()


# Login Page
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


if not st.session_state.logged_in:
    st.title("Hospital Management System")
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
st.title("Hospital Dashboard")
st.write(f"Logged in as: **{st.session_state.role.upper()}**")

# Display system uptime
uptime_seconds = time.time() - st.session_state.system_start_time
uptime_minutes = int(uptime_seconds // 60)
uptime_hours = int(uptime_minutes // 60)
remaining_minutes = uptime_minutes % 60
st.sidebar.info(f"System Uptime: {uptime_hours}h {remaining_minutes}m")

if st.sidebar.button("Logout"):
    log_action(st.session_state.user_id, st.session_state.role, "LOGOUT", "User logged out")
    st.session_state.logged_in = False
    st.rerun()

menu = ["Add Patient", "View Patients", "Edit Patient", "Audit Logs", "Activity Analytics"]
choice = st.sidebar.selectbox("Menu", menu)


# --------------------- Add Patient (Receptionist/Admin) ---------------------
if choice == "Add Patient":
    require_role(["admin", "receptionist"])


    name = st.text_input("Name")
    contact = st.text_input("Contact")
    diagnosis = st.text_input("Diagnosis")


    if st.button("Save"):
        # Input validation
        if not name or not contact or not diagnosis:
            st.error("All fields are required. Please fill in Name, Contact, and Diagnosis.")
        elif len(contact) != 11:
            st.error("Contact number must be of 11 digits.")
        else:
            try:
                anon_name = mask_name(name)
                anon_contact = mask_contact(contact)
                encrypted_diag = encrypt_value(diagnosis)  # Encrypt diagnosis with Fernet
                date_added = datetime.now().strftime("%Y-%m-%d")


                conn = get_connection()
                c = conn.cursor()


                c.execute("INSERT INTO patients (name, contact, diagnosis, anonymized_name, anonymized_contact, date_added, encrypted_diagnosis) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, contact, diagnosis, anon_name, anon_contact, date_added, encrypted_diag))


                conn.commit()
                conn.close()


                log_action(st.session_state.user_id, st.session_state.role, "ADD_PATIENT", name)


                st.success("Patient added successfully!")
                st.info("Diagnosis encrypted with Fernet for secure storage")
            except Exception as e:
                st.error(f"Error adding patient: {str(e)}")
                # Log the error
                try:
                    log_action(st.session_state.user_id, st.session_state.role, "ERROR", f"Failed to add patient: {str(e)}")
                except:
                    pass


# --------------------- Edit Patient (Admin/Receptionist) ---------------------
if choice == "Edit Patient":
    require_role(["admin", "receptionist"])
    
    st.subheader("Edit Patient Record")
    
    try:
        # Fetch all patients
        conn = get_connection()
        patients_df = pd.read_sql_query("SELECT patient_id, name, contact, diagnosis FROM patients", conn)
        conn.close()
        
        if len(patients_df) == 0:
            st.warning("No patients in the system. Please add patients first.")
        else:
            # Create a selection dropdown
            patient_options = {f"{row['patient_id']} - {row['name']}": row['patient_id'] 
                             for _, row in patients_df.iterrows()}
            
            selected_patient = st.selectbox(
                "Select Patient to Edit",
                options=list(patient_options.keys())
            )
            
            if selected_patient:
                patient_id = patient_options[selected_patient]
                
                # Get current patient data
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,))
                patient = c.fetchone()
                conn.close()
                
                if patient:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Current Data:**")
                        st.write(f"Name: {patient[1]}")
                        st.write(f"Contact: {patient[2]}")
                        if st.session_state.role == "admin":
                            st.write(f"Diagnosis: {patient[3]}")
                    
                    with col2:
                        st.write("**Update Data:**")
                        new_name = st.text_input("New Name", value=patient[1])
                        new_contact = st.text_input("New Contact", value=patient[2])
                        
                        # Only admin can edit diagnosis
                        if st.session_state.role == "admin":
                            new_diagnosis = st.text_input("New Diagnosis", value=patient[3])
                        else:
                            st.info("Receptionist cannot edit diagnosis (sensitive data)")
                            new_diagnosis = patient[3]  # Keep existing diagnosis
                    
                    col_update, col_delete = st.columns([1, 1])
                    
                    with col_update:
                        if st.button("Update Patient", type="primary"):
                            # Validation
                            if not new_name or not new_contact or not new_diagnosis:
                                st.error("All fields are required.")
                            elif len(new_contact) != 11:
                                st.error("Contact number must be 11 digits.")
                            else:
                                try:
                                    # Generate new anonymized data
                                    anon_name = mask_name(new_name)
                                    anon_contact = mask_contact(new_contact)
                                    encrypted_diag = encrypt_value(new_diagnosis)
                                    
                                    conn = get_connection()
                                    c = conn.cursor()
                                    c.execute("""UPDATE patients 
                                               SET name=?, contact=?, diagnosis=?, 
                                                   anonymized_name=?, anonymized_contact=?, 
                                                   encrypted_diagnosis=?
                                               WHERE patient_id=?""",
                                            (new_name, new_contact, new_diagnosis, 
                                             anon_name, anon_contact, encrypted_diag, patient_id))
                                    conn.commit()
                                    conn.close()
                                    
                                    log_action(st.session_state.user_id, st.session_state.role, 
                                             "UPDATE_PATIENT", f"Updated patient ID {patient_id}: {new_name}")
                                    
                                    st.success("Patient updated successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating patient: {str(e)}")
                                    log_action(st.session_state.user_id, st.session_state.role, 
                                             "ERROR", f"Failed to update patient: {str(e)}")
                    
                    with col_delete:
                        if st.session_state.role == "admin":
                            if st.button("Delete Patient", type="secondary"):
                                try:
                                    conn = get_connection()
                                    c = conn.cursor()
                                    c.execute("DELETE FROM patients WHERE patient_id=?", (patient_id,))
                                    conn.commit()
                                    conn.close()
                                    
                                    log_action(st.session_state.user_id, st.session_state.role, 
                                             "DELETE_PATIENT", f"Deleted patient ID {patient_id}: {patient[1]}")
                                    
                                    st.success("Patient deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting patient: {str(e)}")
                                    log_action(st.session_state.user_id, st.session_state.role, 
                                             "ERROR", f"Failed to delete patient: {str(e)}")
                        else:
                            st.info("Only admins can delete patients")
                            
    except Exception as e:
        st.error(f"Error loading patient data: {str(e)}")


# --------------------- View Patients (Role-Based View) ---------------------
if choice == "View Patients":
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM patients", conn)
        conn.close()

        # Log VIEW action
        log_action(st.session_state.user_id, st.session_state.role, "VIEW_PATIENTS", f"Viewed {len(df)} patient records")

        role = st.session_state.role


        if role == "doctor":
            # Doctor sees: anonymized identity + FULL diagnosis (needed for treatment)
            display_df = df[["patient_id", "anonymized_name", "anonymized_contact", "diagnosis", "date_added"]]
            st.info("Doctor View: Patient identity anonymized, diagnosis visible for medical treatment")
            st.dataframe(display_df)
            
            # Download button
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Patient Data as CSV",
                data=csv,
                file_name=f"patients_doctor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime='text/csv'
            )


        elif role == "receptionist":
            # Receptionist sees: anonymized identity only, NO diagnosis (not medically trained)
            display_df = df[["patient_id", "anonymized_name", "anonymized_contact", "date_added"]]
            st.info("Receptionist View: Non-sensitive data only (no diagnosis access)")
            st.dataframe(display_df)
            
            # Download button
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Patient Data as CSV",
                data=csv,
                file_name=f"patients_receptionist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime='text/csv'
            )


        else: # admin
            # Decrypt diagnosis for admin view (demonstrating reversible encryption)
            try:
                df['decrypted_diagnosis'] = df['encrypted_diagnosis'].apply(
                    lambda x: decrypt_value(x) if pd.notna(x) and x else df.loc[df['encrypted_diagnosis'] == x, 'diagnosis'].values[0] if not pd.isna(x) else 'N/A'
                )
            except:
                df['decrypted_diagnosis'] = df['diagnosis']
            
            st.info("Admin View: Full access - Diagnosis decrypted using Fernet (reversible encryption)")
            st.dataframe(df)
            
            # Download button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Patient Data as CSV",
                data=csv,
                file_name=f"patients_admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime='text/csv'
            )
    except Exception as e:
        st.error(f"❌ Error loading patient data: {str(e)}")
        try:
            log_action(st.session_state.user_id, st.session_state.role, "ERROR", f"Failed to view patients: {str(e)}")
        except:
            pass


# --------------------- Audit Logs (Admin Only) ---------------------
if choice == "Audit Logs":
    require_role(["admin"])

    try:
        conn = get_connection()
        logs = pd.read_sql_query("SELECT * FROM logs ORDER BY timestamp DESC", conn)
        conn.close()


        st.dataframe(logs)
        
        # Download button
        csv = logs.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Audit Logs as CSV",
            data=csv,
            file_name=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv'
        )
    except Exception as e:
        st.error(f"Error loading audit logs: {str(e)}")


# --------------------- Activity Analytics (Real-time Graphs) ---------------------
if choice == "Activity Analytics":
    st.subheader("Activity Analytics Dashboard")
    
    try:
        conn = get_connection()
        logs = pd.read_sql_query("SELECT * FROM logs", conn)
        conn.close()
        
        if len(logs) == 0:
            st.warning("No activity data available yet. Start using the system to see analytics.")
        else:
            # Convert timestamp to datetime
            logs['timestamp'] = pd.to_datetime(logs['timestamp'])
            logs['date'] = logs['timestamp'].dt.date
            logs['hour'] = logs['timestamp'].dt.hour
            
            # 1. User Actions Per Day
            st.markdown("### User Actions Per Day")
            actions_per_day = logs.groupby('date').size().reset_index(name='count')
            fig1 = px.bar(
                actions_per_day, 
                x='date', 
                y='count',
                title='Daily Activity Overview',
                labels={'date': 'Date', 'count': 'Number of Actions'},
                color='count',
                color_continuous_scale='Blues'
            )
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
            
            # 2. Actions by Type
            st.markdown("### Action Types Distribution")
            action_counts = logs['action'].value_counts().reset_index()
            action_counts.columns = ['action', 'count']
            fig2 = px.pie(
                action_counts,
                values='count',
                names='action',
                title='Action Types Breakdown',
                hole=0.4
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # 3. Activity by Role
            st.markdown("### Activity by User Role")
            role_activity = logs.groupby(['role', 'action']).size().reset_index(name='count')
            fig3 = px.bar(
                role_activity,
                x='role',
                y='count',
                color='action',
                title='User Role Activity Breakdown',
                labels={'role': 'User Role', 'count': 'Number of Actions'},
                barmode='group'
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            # 4. Hourly Activity Heatmap
            st.markdown("### Activity by Hour of Day")
            hourly_activity = logs.groupby('hour').size().reset_index(name='count')
            fig4 = go.Figure(data=[
                go.Bar(
                    x=hourly_activity['hour'],
                    y=hourly_activity['count'],
                    marker_color='lightblue',
                    text=hourly_activity['count'],
                    textposition='auto',
                )
            ])
            fig4.update_layout(
                title='Activity Distribution by Hour',
                xaxis_title='Hour of Day (24h format)',
                yaxis_title='Number of Actions',
                xaxis=dict(tickmode='linear', tick0=0, dtick=1)
            )
            st.plotly_chart(fig4, use_container_width=True)
            
            # # 5. Recent Activity Timeline
            # st.markdown("### Recent Activity Timeline (Last 10 Actions)")
            # recent_logs = logs.sort_values('timestamp', ascending=False).head(10)
            # st.dataframe(
            #     recent_logs[['timestamp', 'role', 'action', 'details']],
            #     use_container_width=True,
            #     hide_index=True
            # )
            
            # # Summary Statistics
            # col1, col2, col3, col4 = st.columns(4)
            # with col1:
            #     st.metric("Total Actions", len(logs))
            # with col2:
            #     st.metric("Unique Users", logs['user_id'].nunique())
            # with col3:
            #     st.metric("Action Types", logs['action'].nunique())
            # with col4:
            #     total_days = (logs['date'].max() - logs['date'].min()).days + 1
            #     avg_actions = len(logs) / total_days if total_days > 0 else len(logs)
            #     st.metric("Avg Actions/Day", f"{avg_actions:.1f}")
                
    except Exception as e:
        st.error(f"Error loading activity analytics: {str(e)}")