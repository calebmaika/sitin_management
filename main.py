import os
from flask import Flask, render_template, request, session, redirect, url_for, flash # type: ignore
from sqlite3 import connect, Row
import sqlite3

app = Flask(__name__)
DATABASE = 'mydb.db'
app.config['SECRET_KEY'] = 'Maika'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def close_db(conn):
    if conn:
    	conn.close()           

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registration WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        close_db(conn)

        if user:
            if user['sessions'] > 0:
                session['username'] = user['username']
                session['IDNO'] = user['IDNO']
                return redirect(url_for('index'))
            else:
                flash("No remaining sessions. Please contact support.", "error")
                return redirect(url_for('login'))
        else:
            flash("Invalid username or password!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        IDNO = request.form['IDNO']
        lastname = request.form['Lastname']
        firstname = request.form['Firstname']
        midname = request.form['Midname']
        course = request.form['Course']
        lvl = request.form['level']
        email = request.form['email']
        address = request.form['address']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return render_template('signup.html', message="Passwords do not match.")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registration WHERE IDNO = ?", (IDNO,))
        existing_IDNO = cursor.fetchone()
        
        if existing_IDNO:
            flash("Existing user ID", "error")
            return redirect(url_for('signup'))    

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registration WHERE username = ?", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash("Existing username", "error")
            return redirect(url_for('signup'))     

        cursor.execute("INSERT INTO registration (IDNO, Lastname, Firstname, Midname, Course, Year_level, email, address, username, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (IDNO, lastname, firstname, midname, course, lvl, email, address, username, password))
        conn.commit()
        close_db(conn)
        
        return redirect(url_for('login')) 
    
    return render_template('signup.html')  

@app.after_request
def after_request(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))  

    if 'IDNO' not in session:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for('login'))

    IDNO = session['IDNO']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registration WHERE IDNO = ?", (IDNO,))
    registration = cursor.fetchone()
    cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC")
    announcements = cursor.fetchall()
    close_db(conn)

    return render_template('index.html', registration=registration, announcements=announcements) 

@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username', None)
        session.pop('IDNO', None)

        flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    IDNO = session['IDNO']

    conn = get_db()
    if not conn:  
        flash("Database connection failed", "error")
        return redirect(url_for('profile'))

    cursor = conn.cursor() 

    if request.method == 'POST':
        lastname = request.form['Lastname']
        firstname = request.form['Firstname']
        midname = request.form['Midname']
        course = request.form['Course']
        lvl = request.form['level']
        email = request.form['email']
        address = request.form['address']

        profile_pic = request.files.get('profile_pic')
        if profile_pic and profile_pic.filename:
            filename = str(IDNO) + "_" + profile_pic.filename.replace(" ", "_")  
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_pic.save(filepath)

            cursor.execute("UPDATE registration SET profile_pic = ? WHERE IDNO = ?", (filename, IDNO))

        cursor.execute("""
            UPDATE registration 
            SET lastname = ?, firstname = ?, midname = ?, course = ?, Year_level = ?, email = ?, address = ? 
            WHERE IDNO = ?
        """, (lastname, firstname, midname, course, lvl, email, address, IDNO))

        conn.commit()
        flash("Profile updated successfully!", "success")
        close_db(conn)  # Close the connection properly

        return redirect(url_for('profile'))

    cursor.execute("SELECT * FROM registration WHERE IDNO = ?", (IDNO,))
    registration = cursor.fetchone()
    close_db(conn)

    return render_template('profile.html', registration=registration)


@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    IDNO = session['IDNO']
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM registration WHERE IDNO = ?", (IDNO,))
        registration = cursor.fetchone()
        if not registration:
            flash("User not found. Please log in again.", "error")
            return redirect(url_for('login'))
    except sqlite3.Error as e:
        flash(f"An error occurred: {e}", "error")
        return redirect(url_for('login'))
    finally:
        close_db(conn)

    return render_template('profile.html', registration=registration)

@app.route('/announcements')
def view_announcements():
    if 'username' not in session:
        flash("You must log in to view announcements.", "error")
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC")
    announcements = cursor.fetchall()
    close_db(conn)

    return render_template('announcements.html', announcements=announcements)

@app.route('/lab_rules')
def lab_rules():
    if 'username' not in session:
        flash("You must log in to view the lab rules.", "error")
        return redirect(url_for('login'))
    
    return render_template('labRules.html')

@app.route('/student_sit_in_history')
def student_sit_in_history():
    if 'username' not in session:
        flash("You must log in to view your sit-in history.", "error")
        return redirect(url_for('login'))

    # Get the student's ID from the session
    student_idno = session.get('IDNO')

    conn = get_db()
    cursor = conn.cursor()

    # Fetch the student's sit-in history
    cursor.execute("""
        SELECT sit_in_records.*, registration.Firstname, registration.Midname, registration.Lastname
        FROM sit_in_records
        JOIN registration ON sit_in_records.student_idno = registration.IDNO
        WHERE sit_in_records.student_idno = ?
        ORDER BY sit_in_records.sit_in_time DESC
    """, (student_idno,))

    sit_in_records = cursor.fetchall()
    close_db(conn)

    # Render the student's sit-in history page
    return render_template('student_sit_in_history.html', sit_in_records=sit_in_records)
    
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if 'username' not in session:
        flash("You must log in to submit feedback.", "error")
        return redirect(url_for('login'))

    sit_in_id = request.form['sit_in_id']
    comment = request.form['comment']

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Update the feedback in the database
        cursor.execute("""
            UPDATE sit_in_records
            SET feedback = ?
            WHERE id = ?
        """, (comment, sit_in_id))

        conn.commit()
        flash("Feedback submitted successfully.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"An error occurred: {e}", "error")
    finally:
        close_db(conn)

    return redirect(url_for('student_sit_in_history'))

@app.route('/delete_feedback', methods=['POST'])
def delete_feedback():
    if 'username' not in session:
        flash("You must log in to delete feedback.", "error")
        return redirect(url_for('login'))

    sit_in_id = request.form['sit_in_id']

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Delete the feedback from the database
        cursor.execute("""
            UPDATE sit_in_records
            SET feedback = NULL
            WHERE id = ?
        """, (sit_in_id,))

        conn.commit()
        flash("Feedback deleted successfully.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"An error occurred: {e}", "error")
    finally:
        close_db(conn)

    return redirect(url_for('student_sit_in_history'))

#4dmin 

# Admin Registration Route
@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('admin_register'))

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = ?", (username,))
        existing_admin = cursor.fetchone()

        if existing_admin:
            flash("Username already exists.", "error")
            return redirect(url_for('admin_register'))

        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        close_db(conn)

        flash("Admin account created successfully. Please log in.", "success")
        return redirect(url_for('admin_login'))

    return render_template('admin_register.html')

# Admin Login Route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = ? AND password = ?", (username, password))
        admin = cursor.fetchone()
        close_db(conn)

        if admin:
            session['admin_username'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

# Admin Dashboard Route
@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    search_results = None
    if request.method == 'POST':
        idno = request.form.get('idno', '').strip()
        if idno:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM registration WHERE IDNO = ?", (idno,))
            search_results = cursor.fetchone()
            close_db(conn)

    return render_template('admin_dashboard.html', search_results=search_results)

# Admin Logout Route
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('admin_login'))

#studentlist
@app.route('/admin/studentlist')
def admin_studentlist():
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registration")
    students = cursor.fetchall()
    close_db(conn)

    return render_template('admin_studentlist.html', students=students)

#Admin can delete student/s
@app.route('/admin/delete_student/<int:idno>', methods=['POST'])
def admin_deletestudent(idno):
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM registration WHERE IDNO = ?", (idno,))
    conn.commit()
    close_db(conn)

    flash("Student deleted successfully.", "success")
    return redirect(url_for('admin_studentlist'))

@app.route('/record_sit_in/<int:idno>', methods=['POST'])
def record_sit_in(idno):
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    lab_room = request.form['lab_room']
    purpose = request.form['purpose']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sit_in_records (student_idno, lab_room, purpose, sit_in_time)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (idno, lab_room, purpose))
    conn.commit()
    close_db(conn)

    flash("Sit-in recorded successfully.", "success")
    return redirect(url_for('current_sit_in_records'))

#sit in records
@app.route('/admin/current_sit_in_records')
def current_sit_in_records():
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sit_in_records.*, registration.Firstname, registration.Midname, 
            registration.Lastname, registration.Year_level
        FROM sit_in_records
        JOIN registration ON sit_in_records.student_idno = registration.IDNO
        WHERE sit_in_records.time_out IS NULL
        ORDER BY sit_in_records.sit_in_time DESC
    """)

    sit_in_records = cursor.fetchall()
    close_db(conn)

    return render_template('current_sit_in_records.html', sit_in_records=sit_in_records)

#admin time out student
@app.route('/timeout_student/<int:id>', methods=['POST'])
def timeout_student(id):
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT student_idno FROM sit_in_records WHERE id = ?", (id,))
        student = cursor.fetchone()

        if student:
            student_idno = student['student_idno']

            cursor.execute("UPDATE registration SET sessions = sessions - 1 WHERE IDNO = ?", (student_idno,))
            cursor.execute("UPDATE sit_in_records SET time_out = CURRENT_TIMESTAMP WHERE id = ?", (id,))

            conn.commit()
            flash("Student timed out successfully. Session deducted.", "success")
        else:
            flash("Student not found in sit-in records.", "error")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"An error occurred: {e}", "error")
    finally:
        close_db(conn)

    return redirect(url_for('current_sit_in_records'))

#admin creating announcements
@app.route('/admin/announcement', methods=['GET', 'POST'])
def admin_announcement():
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        cursor.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", (title, content))
        conn.commit()

        flash("Announcement created successfully.", "success")
        return redirect(url_for('admin_announcement'))
    
    cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC")
    announcements = cursor.fetchall()
    close_db(conn)

    return render_template('admin_announcement.html', announcements=announcements)

#edit announcements
@app.route('/admin/edit_announcement/<int:idno>', methods=['GET', 'POST'])
def admin_edit_announcement(idno):
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        cursor.execute("UPDATE announcements SET title = ?, content = ? WHERE idno = ?", (title, content, idno))
        conn.commit()
        close_db(conn)

        flash("Announcement updated successfully.", "success")
        return redirect(url_for('admin_announcement'))

    cursor.execute("SELECT * FROM announcements WHERE idno = ?", (idno,))
    announcement = cursor.fetchone()
    close_db(conn)

    return render_template('admin_edit_announcement.html', announcement=announcement)

#can delete announcements
@app.route('/admin/delete_announcement/<int:idno>', methods=['POST'])
def admin_delete_announcement(idno):
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM announcements WHERE idno = ?", (idno,))
    conn.commit()
    close_db(conn)

    flash("Announcement deleted successfully.", "success")
    return redirect(url_for('admin_announcement'))

#admin sit in history
@app.route('/admin/sit_in_history')
def admin_sit_in_history():
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    # Get filter parameters from request
    lab_room = request.args.get('lab_room')
    purpose = request.args.get('purpose')
    year_level = request.args.get('Year_level')

    query = """
        SELECT sit_in_records.*, registration.Firstname, registration.Midname, 
               registration.Lastname, registration.Year_level
        FROM sit_in_records
        JOIN registration ON sit_in_records.student_idno = registration.IDNO
    """
    
    conditions = []
    params = []
    
    if lab_room:
        conditions.append("sit_in_records.lab_room = ?")
        params.append(lab_room)
    
    if purpose:
        conditions.append("sit_in_records.purpose = ?")
        params.append(purpose)
    
    if year_level:
        conditions.append("registration.Year_level = ?")
        params.append(year_level)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY sit_in_records.sit_in_time DESC"
    conn = get_db()
    sit_in_records = conn.execute(query, tuple(params)).fetchall()
    close_db(conn)

    return render_template('admin_sit_in_history.html', sit_in_records=sit_in_records)

#delete history
@app.route('/admin/delete_all_history', methods=['POST'])
def delete_all_history():
    if 'admin_username' not in session:
        flash("You must log in as an admin to perform this action.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Delete all records from sit_in_records
        cursor.execute("DELETE FROM sit_in_records")
        conn.commit()
        flash("All sit-in history has been successfully deleted.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Failed to delete history: {str(e)}", "error")
    finally:
        close_db(conn)

    return redirect(url_for('admin_sit_in_history'))

#feedback
@app.route('/admin/feedback_report')
def admin_feedback_report():
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    # Fetch all feedback from the sit_in_records table
    cursor.execute("""
        SELECT sit_in_records.*, registration.Firstname, registration.Midname, registration.Lastname
        FROM sit_in_records
        JOIN registration ON sit_in_records.student_idno = registration.IDNO
        WHERE sit_in_records.feedback IS NOT NULL
        ORDER BY sit_in_records.sit_in_time DESC
    """)

    feedback_records = cursor.fetchall()
    close_db(conn)

    # Render the feedback report page
    return render_template('admin_feedback_report.html', feedback_records=feedback_records)

#reset session action
@app.route('/admin/reset_sessions/<int:idno>', methods=['POST'])
def reset_student_sessions(idno):
    if 'admin_username' not in session:
        flash("You must log in as an admin to perform this action.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE registration SET sessions = 30 WHERE IDNO = ?", (idno,))
        conn.commit()
        flash("Sessions reset successfully to 30.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Error resetting sessions: {str(e)}", "error")
    finally:
        close_db(conn)

    return redirect(url_for('admin_studentlist'))

if __name__ == '__main__':
    app.run(debug=True)
