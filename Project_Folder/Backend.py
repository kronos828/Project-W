from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime, timedelta
import threading

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "your_secret_key"

# SQLite Database Connection
def get_db_connection():
    conn = sqlite3.connect('library_management.db')
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

# Initialize the database and create the tables (if they don't exist)
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create the seats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seats (
            seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seat_number INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available',
            student_id TEXT,
            location TEXT NOT NULL,
            reserved_until TEXT  -- Added reserved_until column
        )
    ''')
    
    # Insert initial data (100 seats) if the table is empty
    cursor.execute("SELECT COUNT(*) FROM seats")
    if cursor.fetchone()[0] == 0:
        # Library seats (1-50)
        for seat_number in range(1, 51):
            cursor.execute("INSERT INTO seats (seat_number, location) VALUES (?, ?)", (seat_number, 'Library'))
        # Computer Lab seats (1-100)
        for seat_number in range(1, 101):
            cursor.execute("INSERT INTO seats (seat_number, location) VALUES (?, ?)", (seat_number, 'Computer Lab'))
    
    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()

# Function to release reserved seats after 1 minute
def release_reserved_seats():
    while True:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("UPDATE seats SET status='Available', student_id=NULL, reserved_until=NULL WHERE reserved_until <= ?", (now,))
        conn.commit()
        conn.close()
        threading.Event().wait(60)  # Check every minute

# Start the thread to release reserved seats
threading.Thread(target=release_reserved_seats, daemon=True).start()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def do_login():
    student_id = request.form['student_id']
    password = request.form['password']
    
    # Check if the password is the last four digits of the student ID
    if len(student_id) >= 4 and password == student_id[-4:]:
        session['student_id'] = student_id.upper()
        return redirect(url_for('dashboard'))
    
    return "Invalid Credentials. Password must be the last four digits of your Student ID."

@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html')

@app.route('/library')
def library():
    if 'student_id' not in session:
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT seat_id, seat_number, status, student_id FROM seats WHERE location = 'Library'")
    seats = cursor.fetchall()
    conn.close()
    return render_template('availaibility.html', seats=seats, location='Library')

@app.route('/computer_lab')
def computer_lab():
    if 'student_id' not in session:
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT seat_id, seat_number, status, student_id FROM seats WHERE location = 'Computer Lab'")
    seats = cursor.fetchall()
    conn.close()
    return render_template('availaibility.html', seats=seats, location='Computer Lab')

@app.route('/reserve', methods=['POST'])
def reserve_seat():
    if 'student_id' not in session:
        return jsonify({"message": "You must be logged in to reserve a seat.", "status": "error"})
    
    data = request.get_json()
    student_id = data['student_id']
    seat_number = data['seat_number']
    location = data['location']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the student already has a reserved or occupied seat
    cursor.execute("SELECT seat_number FROM seats WHERE student_id = ? AND (status = 'Reserved' OR status = 'Occupied')", (student_id,))
    existing_seat = cursor.fetchone()
    
    if existing_seat:
        conn.close()
        return jsonify({
            "message": "You can only reserve one seat at a time.",
            "status": "error"
        })
    
    # Check if the seat is available
    cursor.execute("SELECT status FROM seats WHERE seat_number = ? AND location = ?", (seat_number, location))
    seat = cursor.fetchone()
    
    if seat and seat['status'] == 'Available':
        # Reserve the seat for 1 minute
        reserved_until = (datetime.now() + timedelta(minutes= 1)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("UPDATE seats SET status='Reserved', student_id=?, reserved_until=? WHERE seat_number=? AND location=?", (student_id, reserved_until, seat_number, location))
        conn.commit()
        conn.close()
        return jsonify({
            "message": "Seat reserved successfully for 1 minute!",
            "status": "success",
            "seat_status": "Reserved"
        })
    else:
        conn.close()
        return jsonify({
            "message": "Seat is not available for reservation.",
            "status": "error"
        })

@app.route('/occupy', methods=['POST'])
def occupy_seat():
    if 'student_id' not in session:
        return jsonify({"message": "You must be logged in to occupy a seat.", "status": "error"})
    
    data = request.get_json()
    student_id = data['student_id']
    seat_number = data['seat_number']
    location = data['location']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the seat is reserved by the same student
    cursor.execute("SELECT status, student_id FROM seats WHERE seat_number = ? AND location = ?", (seat_number, location))
    seat = cursor.fetchone()
    
    if seat and seat['status'] == 'Reserved' and seat['student_id'] == student_id:
        # Occupy the seat
        cursor.execute("UPDATE seats SET status='Occupied', reserved_until=NULL WHERE seat_number=? AND location=?", (seat_number, location))
        conn.commit()
        conn.close()
        return jsonify({
            "message": "Seat occupied successfully!",
            "status": "success",
            "seat_status": "Occupied"
        })
    else:
        conn.close()
        return jsonify({
            "message": "You cannot occupy this seat. It is either not reserved or reserved by another student.",
            "status": "error"
        })

@app.route('/cancel', methods=['POST'])
def cancel_seat():
    if 'student_id' not in session:
        return jsonify({"message": "You must be logged in to cancel a reservation.", "status": "error"})
    
    data = request.get_json()
    student_id = data['student_id']
    seat_number = data['seat_number']
    location = data['location']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the seat is reserved or occupied by the same student
    cursor.execute("SELECT status, student_id FROM seats WHERE seat_number = ? AND location = ?", (seat_number, location))
    seat = cursor.fetchone()
    
    if seat and (seat['status'] == 'Reserved' or seat['status'] == 'Occupied') and seat['student_id'] == student_id:
        # Cancel the reservation or occupation
        cursor.execute("UPDATE seats SET status='Available', student_id=NULL, reserved_until=NULL WHERE seat_number=? AND location=?", (seat_number, location))
        conn.commit()
        conn.close()
        return jsonify({
            "message": "Reservation canceled successfully!",
            "status": "success",
            "seat_status": "Available"
        })
    else:
        conn.close()
        return jsonify({
            "message": "You cannot cancel this reservation.",
            "status": "error"
        })

@app.route('/logout')
def logout():
    session.pop('student_id', None)
    return redirect(url_for('index'))

# New route for the user dashboard
@app.route('/user_dashboard')
def user_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('index'))
    
    student_id = session['student_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch the user's reserved and occupied seats, sorted by reservation/occupation date (latest first)
    cursor.execute("""
        SELECT seat_number, location, status, reserved_until 
        FROM seats 
        WHERE student_id = ? 
        ORDER BY reserved_until DESC
    """, (student_id,))
    user_seats = cursor.fetchall()
    
    conn.close()
    
    return render_template('user_dashboard.html', user_seats=user_seats)

if __name__ == '__main__':
    app.run(debug=True)