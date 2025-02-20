import os
from flask import Flask, render_template, request, session, redirect, url_for, flash
from sqlite3 import connect, Row
import sqlite3

app = Flask(__name__)
DATABASE = 'registration.db'
app.config['SECRET_KEY'] = 'Maika'

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
    close_db(conn)

    return render_template('index.html', registration=registration) 

@app.route('/logout')
def logout():
    if 'username' in session:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE registration SET sessions = sessions - 1 WHERE username = ?", (session['username'],))
        conn.commit()
        close_db(conn)

        session.pop('username', None)
        session.pop('IDNO', None)

        flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        IDNO = session['IDNO']
        lastname = request.form['Lastname']
        firstname = request.form['Firstname']
        midname = request.form['Midname']
        course = request.form['Course']
        lvl = request.form['level']
        email = request.form['email']
        address = request.form['address']

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE registration SET lastname = ?, firstname = ?, midname = ?, course = ?, Year_level = ?, email = ?, address = ? WHERE IDNO = ?",
                (lastname, firstname, midname, course, lvl, email, address, IDNO)
            )
            conn.commit()
            flash("Profile updated successfully!", "success")  # Success notif
        except sqlite3.Error as e:
            flash(f"An error occurred: {e}", "error")  
        finally:
            close_db(conn)

        return redirect(url_for('profile'))

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
        return redirect(url_for('profile'))
    finally:
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

if __name__ == '__main__':
    app.run(debug=True)
