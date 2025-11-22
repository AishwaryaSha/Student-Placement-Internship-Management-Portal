"""
Placement Portal (Streamlit + MySQL) — Admin + Student only
===========================================================

Run:
  1) mysql -u root -p < portal.sql
  2) pip install streamlit mysql-connector-python python-dotenv
  3) python -m streamlit run app.py

.env (optional; same folder):
  DB_HOST=localhost
  DB_USER=portal_admin
  DB_PASSWORD=adminpass
  DB_NAME=placement_portal
"""

import os
import hashlib
import datetime
from typing import Optional, Tuple, List, Dict, Any

import streamlit as st
import mysql.connector
from mysql.connector import Error

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env", override=True)
except Exception:
    pass

# =========================
# CONFIG & HELPERS
# =========================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "portal_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "adminpass")
DB_NAME = os.getenv("DB_NAME", "placement_portal")

STATUS_COLORS = {
    "APPLIED": "#2563eb",
    "SHORTLISTED": "#f59e0b",
    "INTERVIEW_SCHEDULED": "#f97316",
    "OFFERED": "#22c55e",
    "REJECTED": "#6b7280",
    "WITHDRAWN": "#9ca3af"
}
INTERVIEW_RESULT_COLORS = {
    "PENDING": "#6b7280",
    "PASS": "#16a34a",
    "FAIL": "#ef4444",
    "RESCHEDULED": "#f59e0b"
}

def get_conn():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def query(sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        if conn: conn.close()

def execute(sql: str, params: Tuple = ()) -> int:
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount
    finally:
        if conn: conn.close()

def call_proc(name: str, args: Tuple):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.callproc(name, args)
        for _ in cur.stored_results():
            pass
        conn.commit()
    finally:
        if conn: conn.close()

def badge(text: str, color: str) -> str:
    return f"""<span style="padding:2px 8px;border-radius:12px;background:{color};color:white;font-size:12px;">{text}</span>"""

def expired_badge() -> str:
    return f"""<span style="padding:2px 8px;border-radius:12px;background:#ef4444;color:white;font-size:12px;">EXPIRED</span>"""

def combine_date_time(d: datetime.date, t: datetime.time) -> datetime.datetime:
    return datetime.datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)

# =========================
# AUTH
# =========================
def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    rows = query(
        "SELECT user_id, username, password_hash, role, student_id FROM users WHERE username=%s",
        (username,)
    )
    if not rows:
        return None
    u = rows[0]
    if u["password_hash"] == sha256_hex(password):
        return {
            "user_id": u["user_id"],
            "username": u["username"],
            "role": u["role"],
            "student_id": u["student_id"],
        }
    return None

def login_ui():
    st.title("🔐 Placement Portal — Login")
    with st.form("login_form"):
        c1, c2 = st.columns(2)
        with c1:
            username = st.text_input("Username", placeholder="admin / aarav")
        with c2:
            password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            user = authenticate(username, password)
            if user:
                st.session_state.auth = user
                st.success(f"Welcome, {user['username']} ({user['role']})")
                st.rerun()  # (Streamlit >= 1.23) replaces experimental_rerun
            else:
                st.error("Invalid credentials.")

# =========================
# ADMIN PAGES
# =========================
def page_students():
    st.header("👩‍🎓 Students — CRUD")
    st.caption("Batch is graduation year (4 digits). Sorted by Student ID.")

    with st.expander("➕ Add Student"):
        with st.form("add_student"):
            c1, c2, c3 = st.columns(3)
            with c1:
                roll = st.text_input("Roll No*", max_chars=32)
                first = st.text_input("First Name*", max_chars=100)
                dept = st.text_input("Department*", max_chars=100)
            with c2:
                last = st.text_input("Last Name*", max_chars=100)
                batch = st.text_input("Batch (Year)*", placeholder="2027")
                cgpa = st.text_input("CGPA*", placeholder="8.50")
            with c3:
                email = st.text_input("Email*", placeholder="name@example.com")
                phone = st.text_input("Phone", placeholder="98765...")
            submit = st.form_submit_button("Create")
            if submit:
                if not (roll and first and last and dept and email and batch and cgpa):
                    st.error("Please fill all required fields.")
                elif not (batch.isdigit() and len(batch)==4):
                    st.error("Batch must be a 4-digit year.")
                else:
                    try:
                        execute("""
                            INSERT INTO student(roll_no, first_name, last_name, email, phone, department, batch, cgpa)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (roll, first, last, email, phone, dept, int(batch), float(cgpa)))
                        st.success("Student created.")
                    except Error as e:
                        st.error(f"MySQL Error: {e}")

    students = query("SELECT * FROM student ORDER BY student_id ASC")
    for row in students:
        st.markdown("---")
        c1, c2, c3, c4 = st.columns([3,3,3,2])
        with c1:
            st.write(f"**#{row['student_id']} — {row['first_name']} {row['last_name']}**")
            st.write(f"Roll: {row['roll_no']}")
        with c2:
            st.write(f"Dept: {row['department']}")
            st.write(f"Batch: {row['batch']}  |  CGPA: {row['cgpa']}")
        with c3:
            st.write(f"Email: {row['email']}")
            st.write(f"Phone: {row['phone']}")
        with c4:
            if st.button("View Applications", key=f"viewapps_{row['student_id']}"):
                apps = query("""
                    SELECT a.application_id, o.title, o.company, a.applied_on, a.status, a.remarks
                    FROM application a
                    JOIN opportunity o ON o.opportunity_id = a.opportunity_id
                    WHERE a.student_id=%s
                    ORDER BY a.applied_on DESC
                """, (row['student_id'],))
                if apps:
                    for a in apps:
                        st.write(f"- **App #{a['application_id']}** — {a['title']} @ {a['company']} on {a['applied_on']}")
                        st.markdown(badge(a['status'], STATUS_COLORS.get(a['status'], '#999')), unsafe_allow_html=True)
                        if a['remarks']:
                            st.caption(a['remarks'])
                else:
                    st.info("No applications yet.")

        with st.expander(f"✏️ Edit / 🗑️ Delete — Student #{row['student_id']}"):
            with st.form(f"edit_student_{row['student_id']}"):
                colA, colB, colC, colD = st.columns(4)
                with colA:
                    first = st.text_input("First Name", value=row['first_name'])
                    dept = st.text_input("Department", value=row['department'])
                with colB:
                    last = st.text_input("Last Name", value=row['last_name'])
                    batch = st.text_input("Batch (Year)", value=str(row['batch']))
                with colC:
                    email = st.text_input("Email", value=row['email'])
                    cgpa = st.text_input("CGPA", value=str(row['cgpa']))
                with colD:
                    phone = st.text_input("Phone", value=row['phone'])
                    roll = st.text_input("Roll No", value=row['roll_no'])
                ubtn = st.form_submit_button("Update")
                if ubtn:
                    try:
                        execute("""
                          UPDATE student SET roll_no=%s, first_name=%s, last_name=%s, email=%s, phone=%s,
                            department=%s, batch=%s, cgpa=%s WHERE student_id=%s
                        """, (roll, first, last, email, phone, dept, int(batch), float(cgpa), row['student_id']))
                        st.success("Updated.")
                        st.rerun()
                    except Error as e:
                        st.error(f"MySQL Error: {e}")

            if st.button("Delete Student", key=f"delstu_{row['student_id']}"):
                try:
                    execute("DELETE FROM student WHERE student_id=%s", (row['student_id'],))
                    st.warning("Student deleted.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

def page_opportunities_admin():
    st.header("💼 Opportunities (Admin)")
    # List & add
    rows = query("""
      SELECT o.*, fn_days_left_for_opportunity(o.opportunity_id) AS days_left
      FROM opportunity o
      ORDER BY o.posted_on DESC, o.opportunity_id DESC
    """)
    for r in rows:
        st.markdown("---")
        c1, c2, c3, c4 = st.columns([3,2,2,3])
        with c1:
            st.write(f"**{r['title']}**")
            st.caption(r['company'])
        with c2:
            st.write(f"Min CGPA: **{r['min_cgpa']}**")
            st.write(f"Vacancy: **{r['vacancy']}**")
        with c3:
            st.write(f"Last Date: {r['application_deadline']}")
            if r['days_left'] is None:
                st.markdown(badge("No Deadline", "#6b7280"), unsafe_allow_html=True)
            elif r['days_left'] < 0:
                st.markdown(expired_badge(), unsafe_allow_html=True)
            else:
                st.markdown(badge(f"{r['days_left']} days left", "#2563eb"), unsafe_allow_html=True)
        with c4:
            if st.button("Delete", key=f"delopp_{r['opportunity_id']}"):
                try:
                    execute("DELETE FROM opportunity WHERE opportunity_id=%s", (r['opportunity_id'],))
                    st.warning("Opportunity deleted.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

    with st.expander("➕ Add Opportunity"):
        with st.form("add_opp"):
            col1, col2, col3 = st.columns(3)
            offices = query("SELECT office_id, name FROM placement_office ORDER BY office_id")
            office_map = {f"#{o['office_id']} — {o['name']}": o['office_id'] for o in offices}
            with col1:
                office = st.selectbox("Placement Office*", list(office_map.keys()))
                title = st.text_input("Title*", max_chars=200)
            with col2:
                company = st.text_input("Company*", max_chars=200)
                vacancy = st.number_input("Vacancy*", min_value=0, value=1)
            with col3:
                mincg = st.number_input("Min CGPA*", min_value=0.0, max_value=10.0, step=0.1, value=7.0)
                deadline = st.date_input("Application Deadline (optional)", value=None)
            desc = st.text_area("Description")
            sb = st.form_submit_button("Create")
            if sb:
                try:
                    execute("""
                      INSERT INTO opportunity(office_id, title, company, description, vacancy, min_cgpa, posted_on, application_deadline)
                      VALUES (%s,%s,%s,%s,%s,%s,CURDATE(),%s)
                    """, (office_map[office], title, company, desc, int(vacancy), float(mincg),
                          deadline if deadline else None))
                    st.success("Opportunity created.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

def page_announcements_admin():
    st.header("📣 Announcements (Admin)")
    with st.expander("➕ Post Announcement"):
        with st.form("add_ann"):
            offices = query("SELECT office_id, name FROM placement_office ORDER BY office_id")
            office_map = {"-- none (global) --": None}
            for o in offices:
                office_map[f"#{o['office_id']} — {o['name']}"] = o['office_id']
            title = st.text_input("Title*")
            content = st.text_area("Content*")
            office_sel = st.selectbox("Office", list(office_map.keys()))
            valid_until = st.date_input("Valid Until (optional)", value=None)
            sb = st.form_submit_button("Post")
            if sb:
                try:
                    execute("""
                      INSERT INTO announcement(office_id, title, content, valid_until)
                      VALUES (%s,%s,%s,%s)
                    """, (office_map[office_sel], title, content, valid_until if valid_until else None))
                    st.success("Announcement posted.")
                except Error as e:
                    st.error(f"MySQL Error: {e}")

    anns = query("""
      SELECT a.announcement_id, a.title, a.content, a.post_date, a.valid_until, p.name AS office_name
      FROM announcement a
      LEFT JOIN placement_office p ON p.office_id = a.office_id
      ORDER BY a.post_date DESC
    """)
    for a in anns:
        st.markdown("---")
        st.write(f"**{a['title']}**  —  {a['office_name'] or 'Global'}")
        st.caption(f"Posted: {a['post_date']}  |  Valid until: {a['valid_until'] or '—'}")
        st.write(a['content'])
        if st.button("Delete", key=f"delann_{a['announcement_id']}"):
            try:
                execute("DELETE FROM announcement WHERE announcement_id=%s", (a['announcement_id'],))
                st.warning("Announcement deleted.")
                st.rerun()
            except Error as e:
                st.error(f"MySQL Error: {e}")

def page_assessments_admin():
    st.header("📝 Assessments (Admin)")
    with st.expander("➕ Add Assessment"):
        with st.form("add_assessment"):
            opps = query("SELECT opportunity_id, title, company FROM opportunity ORDER BY opportunity_id DESC")
            opp_map = {f"#{o['opportunity_id']} — {o['title']} @ {o['company']}": o['opportunity_id'] for o in opps}
            opp_sel = st.selectbox("Opportunity*", list(opp_map.keys()))
            title = st.text_input("Title*", max_chars=200)
            max_marks = st.number_input("Max Marks*", min_value=1, value=100)
            d = st.date_input("Date*", value=(datetime.date.today() + datetime.timedelta(days=2)))
            t = st.time_input("Time*", value=datetime.time(10, 0))
            mode = st.selectbox("Mode*", ["ONLINE","OFFLINE"])
            duration = st.number_input("Duration (minutes, ONLINE only)", min_value=0, value=90 if mode=="ONLINE" else 0)
            desc = st.text_area("Description")
            sb = st.form_submit_button("Create")
            if sb:
                try:
                    execute("""
                      INSERT INTO assessment (opportunity_id, title, max_marks, date_scheduled, mode, duration_minutes, description)
                      VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, (opp_map[opp_sel], title, int(max_marks), combine_date_time(d,t), mode,
                          int(duration) if mode=="ONLINE" else None, desc))
                    st.success("Assessment added.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

    rows = query("""
      SELECT a.assessment_id, a.title, a.max_marks, a.date_scheduled, a.mode, a.duration_minutes, a.description,
             o.title AS opp_title, o.company
      FROM assessment a
      JOIN opportunity o ON o.opportunity_id = a.opportunity_id
      ORDER BY a.date_scheduled DESC
    """)
    for r in rows:
        st.markdown("---")
        st.write(f"**{r['title']}** — {r['max_marks']} marks")
        extra = f" | Mode: {r['mode']}"
        if r['mode'] == "ONLINE" and r['duration_minutes']:
            extra += f" | Duration: {r['duration_minutes']} mins"
        st.caption(f"For: {r['opp_title']} @ {r['company']}  |  Scheduled: {r['date_scheduled']}{extra}")
        if r['description']:
            st.write(r['description'])
        if st.button("Delete", key=f"delassess_{r['assessment_id']}"):
            try:
                execute("DELETE FROM assessment WHERE assessment_id=%s", (r['assessment_id'],))
                st.warning("Assessment deleted.")
                st.rerun()
            except Error as e:
                st.error(f"MySQL Error: {e}")

def page_interviews_admin():
    st.header("🎤 Interviews (Admin: schedule via procedure)")
    with st.expander("📅 Schedule Interview (sp_schedule_interview)"):
        with st.form("schedule_interview"):
            apps = query("""
              SELECT a.application_id, s.first_name, s.last_name, o.title, o.company
              FROM application a
              JOIN student s ON s.student_id=a.student_id
              JOIN opportunity o ON o.opportunity_id=a.opportunity_id
              ORDER BY a.application_id DESC
            """)
            app_map = {f"#{a['application_id']} — {a['first_name']} {a['last_name']} for {a['title']} @ {a['company']}": a['application_id'] for a in apps}
            sel = st.selectbox("Application*", list(app_map.keys()) if app_map else [])
            d = st.date_input("Date*", value=(datetime.date.today() + datetime.timedelta(days=1)))
            t = st.time_input("Time*", value=datetime.time(11, 0))
            mode = st.selectbox("Mode*", ["ONLINE","OFFLINE"])
            venue = st.text_input("Venue / Link*", value=("Google Meet" if mode=="ONLINE" else "Placement Cell, Room 101"))
            panel = st.text_area("Panel*", value="HR; Tech Lead")
            sb = st.form_submit_button("Schedule")
            if sb:
                try:
                    call_proc("sp_schedule_interview", (app_map[sel], combine_date_time(d,t), mode, venue, panel))
                    st.success("Interview scheduled and application status updated.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

    rows = query("""
      SELECT i.interview_id, i.application_id, i.schedule_time, i.mode, i.venue, i.panel, i.result,
             s.first_name, s.last_name, o.title AS opp_title, o.company
      FROM interview i
      JOIN application a ON a.application_id = i.application_id
      JOIN student s ON s.student_id = a.student_id
      JOIN opportunity o ON o.opportunity_id = a.opportunity_id
      ORDER BY i.schedule_time DESC
    """)
    for r in rows:
        st.markdown("---")
        c1,c2,c3 = st.columns([3,2,2])
        with c1:
            st.write(f"**#{r['interview_id']} — {r['first_name']} {r['last_name']}**")
            st.caption(f"{r['opp_title']} @ {r['company']}")
            st.write(f"When: {r['schedule_time']}  |  Mode: {r['mode']}")
        with c2:
            st.write(f"Venue/Link: {r['venue']}")
            st.write(f"Panel: {r['panel']}")
        with c3:
            st.markdown(badge(f"Result: {r['result']}", INTERVIEW_RESULT_COLORS.get(r['result'], "#666")), unsafe_allow_html=True)
            newres = st.selectbox("Update Result", ["PENDING","PASS","FAIL","RESCHEDULED"],
                                  index=["PENDING","PASS","FAIL","RESCHEDULED"].index(r['result']),
                                  key=f"res_{r['interview_id']}")
            if st.button("Save Result", key=f"svres_{r['interview_id']}"):
                try:
                    execute("UPDATE interview SET result=%s WHERE interview_id=%s", (newres, r['interview_id']))
                    st.success("Result updated.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

def page_applications_admin():
    st.header("🗂️ Applications (Admin)")
    rows = query("""
      SELECT a.application_id, a.applied_on, a.status, a.remarks,
             s.student_id, CONCAT(s.first_name,' ',s.last_name) AS student_name,
             o.opportunity_id, o.title, o.company
      FROM application a
      JOIN student s ON s.student_id=a.student_id
      JOIN opportunity o ON o.opportunity_id=a.opportunity_id
      ORDER BY a.applied_on DESC
    """)
    for r in rows:
        st.markdown("---")
        c1,c2,c3 = st.columns([3,3,3])
        with c1:
            st.write(f"**App #{r['application_id']}** by **{r['student_name']}**")
            st.caption(f"On: {r['applied_on']}")
        with c2:
            st.write(f"{r['title']} @ {r['company']}")
            if r['remarks']:
                st.caption(f"Remarks: {r['remarks']}")
        with c3:
            st.markdown(badge(r['status'], STATUS_COLORS.get(r['status'], "#666")), unsafe_allow_html=True)
            new_status = st.selectbox("Change Status",
                                      ['APPLIED','SHORTLISTED','INTERVIEW_SCHEDULED','OFFERED','REJECTED','WITHDRAWN'],
                                      index=['APPLIED','SHORTLISTED','INTERVIEW_SCHEDULED','OFFERED','REJECTED','WITHDRAWN'].index(r['status']),
                                      key=f"stsel_{r['application_id']}")
            if st.button("Update Status", key=f"upst_{r['application_id']}"):
                try:
                    execute("UPDATE application SET status=%s WHERE application_id=%s", (new_status, r['application_id']))
                    execute("INSERT INTO application_audit(application_id, action, details) VALUES (%s,'STATUS_CHANGE',%s)",
                            (r['application_id'], f"{r['status']} -> {new_status}"))
                    st.success("Status updated.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

            if st.button("Withdraw", key=f"wd_{r['application_id']}"):
                try:
                    execute("UPDATE application SET status='WITHDRAWN' WHERE application_id=%s", (r['application_id'],))
                    execute("INSERT INTO application_audit(application_id, action, details) VALUES (%s,'WITHDRAW','User action')", (r['application_id'],))
                    st.warning("Application withdrawn.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

            if st.button("Delete Application", key=f"del_{r['application_id']}"):
                try:
                    execute("DELETE FROM application WHERE application_id=%s", (r['application_id'],))
                    st.error("Application deleted (triggers fired).")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

def page_reports():
    st.header("📊 Queries & Reports (Views / Functions)")
    st.caption("Join, aggregate, nested views and function outputs.")

    st.subheader("Join + Aggregate View: vw_opportunity_stats")
    v1 = query("SELECT * FROM vw_opportunity_stats ORDER BY opportunity_id DESC")
    for r in v1:
        st.write(f"- **#{r['opportunity_id']} {r['title']}** @ {r['company']} | Apps: {r['total_applications']} | Avg CGPA: {r['avg_applicant_cgpa']}")

    st.subheader("Aggregate View: vw_student_app_counts")
    v2 = query("SELECT * FROM vw_student_app_counts ORDER BY app_count DESC, student_id ASC")
    for r in v2:
        st.write(f"- **#{r['student_id']} {r['student_name']}** — Dept: {r['department']} | Batch: {r['batch']} | Applications: {r['app_count']}")

    st.subheader("Nested Query View: vw_above_average_applicants")
    v3 = query("SELECT * FROM vw_above_average_applicants ORDER BY app_count DESC")
    if v3:
        st.write("Students whose application count is **above** global average.")
        for r in v3:
            st.write(f"- **#{r['student_id']} {r['student_name']}** — {r['app_count']} applications")
    else:
        st.info("Currently, no one is above average.")

    st.subheader("Function Demos")
    s1 = query("SELECT student_id FROM student ORDER BY student_id LIMIT 1")
    if s1:
        sid = s1[0]["student_id"]
        name_row = query("SELECT fn_get_student_fullname(%s) AS fullname", (sid,))
        st.write(f"fn_get_student_fullname({sid}) → **{name_row[0]['fullname']}**")
    opps = query("SELECT opportunity_id, title FROM opportunity ORDER BY opportunity_id DESC LIMIT 3")
    for o in opps:
        dl = query("SELECT fn_days_left_for_opportunity(%s) AS dl", (o['opportunity_id'],))
        st.write(f"fn_days_left_for_opportunity(#{o['opportunity_id']} {o['title']}) → **{dl[0]['dl']}**")

def page_users_admin():
    st.header("👤 Users (Admin)")
    with st.expander("➕ Create App User"):
        with st.form("add_user"):
            username = st.text_input("Username*", max_chars=100)
            role = st.selectbox("Role*", ["ADMIN","STUDENT"])
            # Optional: link to student for STUDENT role
            students = query("SELECT student_id, CONCAT(first_name,' ',last_name,' (',roll_no,')') AS nm FROM student ORDER BY student_id")
            student_map = {"-- none --": None}
            for s in students:
                student_map[f"#{s['student_id']} — {s['nm']}"] = s['student_id']
            link_label = st.selectbox("Link to Student (for STUDENT)", list(student_map.keys()))
            pwd = st.text_input("Password*", type="password")
            sb = st.form_submit_button("Create")
            if sb:
                try:
                    execute("INSERT INTO users(username, password_hash, role, student_id) VALUES (%s,%s,%s,%s)",
                            (username, sha256_hex(pwd), role, student_map[link_label]))
                    st.success("User created.")
                except Error as e:
                    st.error(f"MySQL Error: {e}")

    users = query("""
      SELECT u.user_id, u.username, u.role, u.created_at, u.student_id,
             CONCAT(s.first_name,' ',s.last_name) AS student_name
      FROM users u
      LEFT JOIN student s ON s.student_id=u.student_id
      ORDER BY u.user_id
    """)
    for u in users:
        link = f" → Student #{u['student_id']} {u['student_name']}" if u['student_id'] else ""
        st.write(f"- **#{u['user_id']} {u['username']}** — {u['role']}{link} (created {u['created_at']})")
        if u['username'] != "admin":
            if st.button("Delete", key=f"delusr_{u['user_id']}"):
                try:
                    execute("DELETE FROM users WHERE user_id=%s", (u['user_id'],))
                    st.warning("User deleted.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

# =========================
# STUDENT PAGES (personalized)
# =========================
def page_student_dashboard(student_id: int):
    st.header("🏠 My Dashboard")
    st.caption("Upcoming interviews and assessments relevant to you.")

    # Upcoming interviews for this student's applications
    st.subheader("🎤 Upcoming Interviews")
    interviews = query("""
      SELECT i.interview_id, i.schedule_time, i.mode, i.venue, i.panel, i.result,
             o.title, o.company
      FROM interview i
      JOIN application a ON a.application_id=i.application_id
      JOIN opportunity o ON o.opportunity_id=a.opportunity_id
      WHERE a.student_id=%s AND i.schedule_time >= NOW()
      ORDER BY i.schedule_time ASC
    """, (student_id,))
    if interviews:
        for r in interviews:
            st.write(f"- **{r['title']} @ {r['company']}**")
            st.caption(f"Date: {r['schedule_time']} | Mode: {r['mode']} | Venue/Link: {r['venue']}")
            st.markdown(badge(f"Status: {r['result']}", INTERVIEW_RESULT_COLORS.get(r['result'], "#666")), unsafe_allow_html=True)
    else:
        st.info("No upcoming interviews.")

    # Upcoming assessments for opportunities this student applied to
    st.subheader("📝 Upcoming Assessments")
    assessments = query("""
      SELECT a2.title AS assess_title, a2.date_scheduled, a2.mode, a2.duration_minutes,
             o.title AS opp_title, o.company
      FROM assessment a2
      JOIN opportunity o ON o.opportunity_id=a2.opportunity_id
      JOIN application ap ON ap.opportunity_id=o.opportunity_id
      WHERE ap.student_id=%s AND a2.date_scheduled >= NOW()
      ORDER BY a2.date_scheduled ASC
    """, (student_id,))
    if assessments:
        for r in assessments:
            extra = f" | Duration: {r['duration_minutes']} mins" if r['mode']=="ONLINE" and r['duration_minutes'] else ""
            st.write(f"- **{r['opp_title']} @ {r['company']}** — {r['assess_title']}")
            st.caption(f"Date: {r['date_scheduled']} | Mode: {r['mode']}{extra}")
    else:
        st.info("No upcoming assessments.")

def page_student_profile(student_id: int):
    st.header("👤 My Profile")
    s = query("SELECT * FROM student WHERE student_id=%s", (student_id,))
    if not s:
        st.error("Student record not found.")
        return
    s = s[0]
    st.write(f"**{s['first_name']} {s['last_name']}**  |  Roll: {s['roll_no']}")
    st.write(f"Dept: {s['department']}  |  Batch: {s['batch']}  |  CGPA: {s['cgpa']}")
    with st.form("update_profile"):
        c1,c2,c3 = st.columns(3)
        with c1:
            email = st.text_input("Email", value=s['email'])
        with c2:
            phone = st.text_input("Phone", value=s['phone'] or "")
        with c3:
            # read-only fields (disable edits)
            st.text_input("Department", value=s['department'], disabled=True)
        note = st.text_area("Notes (not saved)", value="", placeholder="Use admin contact for major changes.")
        sb = st.form_submit_button("Save Contact Info")
        if sb:
            try:
                execute("UPDATE student SET email=%s, phone=%s WHERE student_id=%s", (email, phone, student_id))
                st.success("Contact info updated.")
                st.rerun()
            except Error as e:
                st.error(f"MySQL Error: {e}")

def page_opportunities_student(student_id: int):
    st.header("💼 Opportunities")
    st.caption("Personalized for you. No global student filter; apply directly. EXPIRED items are disabled.")

    # For each opportunity, compute days_left and whether already applied
    rows = query("""
      SELECT 
        o.opportunity_id, o.title, o.company, o.min_cgpa, o.vacancy,
        o.application_deadline, o.posted_on,
        fn_days_left_for_opportunity(o.opportunity_id) AS days_left
      FROM opportunity o
      ORDER BY o.posted_on DESC, o.opportunity_id DESC
    """)
    # Fetch existing applications for this student
    existing = query("SELECT opportunity_id FROM application WHERE student_id=%s", (student_id,))
    applied_set = {e['opportunity_id'] for e in existing}
    # Get student CGPA for quick eligibility hint
    srow = query("SELECT cgpa FROM student WHERE student_id=%s", (student_id,))
    my_cgpa = srow[0]['cgpa'] if srow else 0.0

    for r in rows:
        st.markdown("---")
        c1, c2, c3, c4 = st.columns([3,2,3,2])
        with c1:
            st.write(f"**{r['title']}**")
            st.caption(r['company'])
        with c2:
            st.write(f"Min CGPA: **{r['min_cgpa']}** (You: {my_cgpa})")
            st.write(f"Vacancy: **{r['vacancy']}**")
        with c3:
            st.write(f"Last Date: {r['application_deadline']}")
            if r['days_left'] is None:
                st.markdown(badge("No Deadline", "#6b7280"), unsafe_allow_html=True)
            elif r['days_left'] < 0:
                st.markdown(expired_badge(), unsafe_allow_html=True)
            else:
                st.markdown(badge(f"{r['days_left']} days left", "#2563eb"), unsafe_allow_html=True)
        with c4:
            expired = (r['days_left'] is not None and r['days_left'] < 0)
            already = (r['opportunity_id'] in applied_set)
            disabled = expired or already
            label = "Applied" if already else ("Apply" if not expired else "Expired")
            if st.button(label, key=f"apply_{r['opportunity_id']}", disabled=disabled):
                try:
                    call_proc("sp_create_application", (student_id, r['opportunity_id'], 0))
                    st.success(f"You have successfully applied for **{r['title']} @ {r['company']}**.")
                    st.rerun()
                except Error as e:
                    st.error(f"MySQL Error: {e}")

# =========================
# NAVIGATION
# =========================
PAGES_ADMIN = {
    "Students": page_students,
    "Opportunities": page_opportunities_admin,
    "Announcements": page_announcements_admin,
    "Assessments": page_assessments_admin,
    "Interviews": page_interviews_admin,
    "Applications": page_applications_admin,
    "Reports": page_reports,
    "Users": page_users_admin
}

PAGES_STUDENT = {
    "My Dashboard": page_student_dashboard,
    "My Profile": page_student_profile,
    "Opportunities": page_opportunities_student,
    "Reports": page_reports,  # read-only reports if wanted
}

def main():
    st.set_page_config(page_title="Placement Portal", page_icon="🎓", layout="wide")
    if "auth" not in st.session_state:
        st.session_state.auth = None

    if not st.session_state.auth:
        login_ui()
        return

    auth = st.session_state.auth
    role = auth["role"]
    st.sidebar.title("🎓 Placement Portal")
    st.sidebar.write(f"Logged in as **{auth['username']}** ({role})")
    st.sidebar.caption(f"DB: {DB_USER}@{DB_HOST}/{DB_NAME}")

    if role == "ADMIN":
        page_name = st.sidebar.selectbox("Navigate", list(PAGES_ADMIN.keys()))
        st.sidebar.divider()
        if st.sidebar.button("Logout"):
            st.session_state.auth = None
            st.rerun()
        PAGES_ADMIN[page_name]()

    elif role == "STUDENT":
        if not auth.get("student_id"):
            st.error("This student user is not linked to a student record. Ask Admin to link it.")
            if st.sidebar.button("Logout"):
                st.session_state.auth = None
                st.rerun()
            return
        page_name = st.sidebar.selectbox("Navigate", list(PAGES_STUDENT.keys()))
        st.sidebar.divider()
        if st.sidebar.button("Logout"):
            st.session_state.auth = None
            st.rerun()
        # Call page with student_id
        if page_name in ["My Dashboard", "My Profile", "Opportunities"]:
            PAGES_STUDENT[page_name](auth["student_id"])
        else:
            PAGES_STUDENT[page_name]()

    else:
        st.error("Unknown role.")
        if st.sidebar.button("Logout"):
            st.session_state.auth = None
            st.rerun()

if __name__ == "__main__":
    main()
