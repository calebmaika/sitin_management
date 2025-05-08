import os
from flask import Flask, render_template, request, session, redirect, url_for, flash 
import uuid 
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
        flash("You must log in as an adm​​​​​​in to access this page.", "error")
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

    award_point = request.form.get('award_point', '0') == '1'
    points = 1 if award_point else 0
    bonus_sessions = 0
    
    # Calculate bonus sessions only if points were awarded
    if points > 0:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get student's total points including this new one
        cursor.execute("""
            SELECT COALESCE(SUM(points), 0) + ? AS total_points 
            FROM sit_in_records 
            WHERE student_idno = (SELECT student_idno FROM sit_in_records WHERE id = ?)
        """, (points, id))
        total_points = cursor.fetchone()['total_points']
        bonus_sessions = total_points // 3 - (total_points - points) // 3

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT student_idno FROM sit_in_records WHERE id = ?", (id,))
        student = cursor.fetchone()

        if student:
            student_idno = student['student_idno']

            # Always deduct 1 session for the sit-out
            net_sessions = -1 + bonus_sessions
            
            cursor.execute("""
                UPDATE registration 
                SET sessions = sessions + ? 
                WHERE IDNO = ?""", 
                (net_sessions, student_idno))
            
            cursor.execute("""
                UPDATE sit_in_records 
                SET time_out = CURRENT_TIMESTAMP, points = ? 
                WHERE id = ?""", 
                (points, id))

            conn.commit()
            
            if award_point:
                if bonus_sessions > 0:
                    flash_message = f"Student timed out with 1 point. Earned {bonus_sessions} bonus session(s). Net sessions: {net_sessions}."
                else:
                    flash_message = "Student timed out with 1 point. (Not enough for bonus session yet)"
            else:
                flash_message = "Student timed out with no points. 1 session deducted."
                
            flash(flash_message, "success")
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

#reset all sessions
@app.route('/admin/reset_all_sessions', methods=['POST'])
def reset_all_sessions():
    if 'admin_username' not in session:
        flash("You must log in as an admin to perform this action.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE registration SET sessions = 30")
        conn.commit()
        flash("All student sessions have been reset to 30.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Error resetting sessions: {str(e)}", "error")
    finally:
        close_db(conn)

    return redirect(url_for('admin_studentlist'))

#reset session action per student
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

#resources

@app.route('/resources')
def student_resources():
    if 'username' not in session:
        flash("You must log in to view lab resources.", "error")
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resources ORDER BY created_at DESC")
    resources = cursor.fetchall()
    close_db(conn)

    return render_template('student_resources.html', resources=resources)

@app.route('/admin/resources', methods=['GET', 'POST'])
def admin_resources():
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        status = request.form['status']
        resource_id = request.form.get('resource_id')
        image = request.files.get('image')

        image_path = None
        if image and image.filename:
            # Create uploads directory if it doesn't exist
            upload_dir = app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate a unique filename
            ext = os.path.splitext(image.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(upload_dir, filename)
            
            # Save the file
            image.save(filepath)
            image_path = filename

        if resource_id:  # Editing existing resource
            if image_path:
                # Update with new image
                cursor.execute("""
                    UPDATE resources 
                    SET name=?, description=?, status=?, image_path=?
                    WHERE id=?
                """, (name, description, status, image_path, resource_id))
            else:
                # Update without changing image
                cursor.execute("""
                    UPDATE resources 
                    SET name=?, description=?, status=?
                    WHERE id=?
                """, (name, description, status, resource_id))
        else:  # Adding new resource
            cursor.execute("""
                INSERT INTO resources (name, description, status, image_path)
                VALUES (?, ?, ?, ?)
            """, (name, description, status, image_path))

        conn.commit()
        flash("Resource saved successfully!", "success")
        return redirect(url_for('admin_resources'))

    cursor.execute("SELECT * FROM resources ORDER BY id DESC")
    resources = cursor.fetchall()
    close_db(conn)

    return render_template('admin_resources.html', resources=resources)

@app.route('/admin/delete_resource/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    if 'admin_username' not in session:
        flash("You must log in as an admin to perform this action.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    try:
        # First get the image path to delete the file
        cursor.execute("SELECT image_path FROM resources WHERE id=?", (resource_id,))
        resource = cursor.fetchone()
        if resource and resource['image_path']:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], resource['image_path']))
            except OSError:
                pass  # File doesn't exist or couldn't be deleted
        
        cursor.execute("DELETE FROM resources WHERE id=?", (resource_id,))
        conn.commit()
        flash("Resource deleted successfully!", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Error deleting resource: {str(e)}", "error")
    finally:
        close_db(conn)

    return redirect(url_for('admin_resources'))

@app.route('/admin/leaderboard')
def admin_leaderboard():
    if 'admin_username' not in session:
        flash("You must log in as an admin to access this page.", "error")
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            r.IDNO, 
            r.Firstname, 
            r.Midname, 
            r.Lastname, 
            r.Year_level, 
            r.sessions,
            COALESCE(SUM(s.points), 0) AS total_points,
            COALESCE(SUM(s.points), 0) / 3 AS bonus_sessions_earned,
            (3 - (COALESCE(SUM(s.points), 0) % 3)) % 3 AS points_to_next_bonus
        FROM registration r
        LEFT JOIN sit_in_records s ON r.IDNO = s.student_idno
        GROUP BY r.IDNO
        ORDER BY total_points DESC, r.Lastname
    """)
    
    leaderboard = cursor.fetchall()
    close_db(conn)

    return render_template('admin_leaderboard.html', leaderboard=leaderboard)

if __name__ == '__main__':
    app.run(debug=True)
