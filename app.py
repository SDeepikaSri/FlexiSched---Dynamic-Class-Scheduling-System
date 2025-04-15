from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS teachers (
                        teacher_id TEXT PRIMARY KEY,
                        name TEXT,
                        subject TEXT,
                        time_required INTEGER
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
                        teacher_id TEXT,
                        timestamp TEXT,
                        PRIMARY KEY (teacher_id, timestamp)
                    )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register-page')
def register_page():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    teacher_id = data['teacher_id']
    name = data['name']
    subject = data['subject']
    time_required = data['time_required']

    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO teachers (teacher_id, name, subject, time_required) VALUES (?, ?, ?, ?)',
                   (teacher_id, name, subject, time_required))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Teacher registered successfully'})

@app.route('/schedule', methods=['POST'])
def schedule():
    data = request.get_json()
    subjects = data['subjects']
    times = data['times']
    quantum = int(data['quantum'])

    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()

    # Fetch subjects and teacher names of present teachers
    cursor.execute('''
        SELECT t.subject, t.name FROM teachers t
        JOIN attendance a ON t.teacher_id = a.teacher_id
        GROUP BY t.subject
    ''')
    rows = cursor.fetchall()
    conn.close()

    # Map subjects to teacher names
    subject_teacher_map = {row[0]: row[1] for row in rows}
    present_subjects = list(subject_teacher_map.keys())

    # Filter based on present teachers
    filtered_subjects = []
    filtered_times = []
    for subj, t in zip(subjects, times):
        if subj in present_subjects:
            filtered_subjects.append(subj)
            filtered_times.append(t)

    if not filtered_subjects:
        return jsonify({'message': 'No subjects with present teachers'}), 400

    schedule = round_robin(filtered_subjects, filtered_times, quantum, subject_teacher_map)
    return jsonify(schedule), 200


from datetime import datetime, timedelta

def round_robin(subjects, times, quantum, subject_teacher_map):
    start_time = datetime.strptime("09:00", "%H:%M")
    break_start = datetime.strptime("12:30", "%H:%M")
    break_end = datetime.strptime("14:00", "%H:%M")
    end_time = datetime.strptime("17:00", "%H:%M")

    subjects_times = list(zip(subjects, times))
    schedule = []

    while subjects_times and start_time < end_time:
        subject, time_needed = subjects_times.pop(0)
        teacher = subject_teacher_map.get(subject, "Unknown")

        time_to_allocate = min(time_needed, quantum)
        next_time = start_time + timedelta(hours=time_to_allocate)

        # Handle break time overlap
        if start_time < break_start and next_time > break_start:
            time_to_allocate = (break_start - start_time).seconds / 3600
            next_time = start_time + timedelta(hours=time_to_allocate)

        if start_time >= break_start and start_time < break_end:
            start_time = break_end
            next_time = start_time
            subjects_times.insert(0, (subject, time_needed))
            continue

        if next_time > end_time:
            break

        # Add schedule entry
        schedule.append({
            'teacher': teacher,
            'subject': subject,
            'time_start': start_time.strftime("%I:%M %p"),
            'time_end': next_time.strftime("%I:%M %p")
        })

        if time_needed > quantum:
            remaining_time = time_needed - quantum
            subjects_times.append((subject, remaining_time))

        start_time = next_time

    return schedule


@app.route('/attendance', methods=['POST'])
def attendance():
    data = request.get_json()
    teacher_id = data['teacher_id']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO attendance (teacher_id, timestamp) VALUES (?, ?)',
                   (teacher_id, timestamp))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Attendance marked successfully'})

# New RFID Endpoint
@app.route('/rfid', methods=['POST'])
def rfid():
    data = request.get_json()
    teacher_id = data['uid']  # RFID ID received from the ESP8266
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Validate teacher_id (Check if the teacher exists in the database)
    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM teachers WHERE teacher_id = ?', (teacher_id,))
    teacher = cursor.fetchone()

    if teacher:
        # If teacher exists, log attendance
        cursor.execute('INSERT INTO attendance (teacher_id, timestamp) VALUES (?, ?)',
                       (teacher_id, timestamp))
        conn.commit()
        conn.close()
        return jsonify({'message': f'Attendance for {teacher[1]} marked successfully at {timestamp}'})
    else:
        conn.close()
        return jsonify({'message': 'Teacher not found. Attendance could not be marked.'}), 404

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)