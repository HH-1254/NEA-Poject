import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for, session
from datetime import datetime, timedelta
import calendar


 # Replace with a secure key

app = Flask(__name__)
app.secret_key = "your_secret_key_here"


#List for tasks
tasks = []
#List for emails if a reset is needed
user_email_temp = {"email": "", "code": ""}


#Initalise Database
connection = sqlite3.connect("NEA.db")
cursor = connection.cursor()


#Table for login system
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        security_code TEXT NOT NULL
    )
""")


#Table for Task management
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        due_date TEXT NOT NULL,
        label TEXT,
        progress INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")




# Table for Completed Tasks
cursor.execute("""
    CREATE TABLE IF NOT EXISTS completed_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        due_date TEXT NOT NULL,
        label TEXT,
        progress INTEGER DEFAULT 100,
        completed_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")



# Events table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")





connection.commit()
connection.close()




# Create login form in html
login_form = """
<!doctype html>
<html>
<head>
    <title>Login</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
        <h2>Login</h2>
        <form method="POST">
            <label>Email:</label><br>
            <input type="text" name="email" required><br><br>

            <label>Password:</label><br>
            <input type="password" name="password" required><br><br>

            <input type="submit" value="Login">
        </form>
        <p style="color:red;">{{ message }}</p>
        <p>Don't have an account? <a href="/register">Register here</a></p>
        <p><a href="/verify">Forgot Password?</a></p>
    </div>
</body>
</body>
</html>
"""

# Create register form in html
register_form = """
<!doctype html>
<html>
<head>
    <title>Register</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>

    <h2>Create an Account</h2>
    <form method="POST">
        <label>Email:</label><br>
        <input type="text" name="email" required><br><br>

        <label>Password (min 8 chars):</label><br>
        <input type="password" name="password" required><br><br>

        <label>Security Code (numbers only):</label><br>
        <input type="text" name="security_code" pattern="\d{6}" required>

        <input type="submit" value="Register">
    </form>
    <p style="color:red;">{{ message }}</p>
    <p>Already have an account? <a href="/">Login here</a></p>
</body>
</html>
"""
# Create forgot form in html
reset_form = """
<!doctype html>
<html>
<head>
    <title>Reset Password</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>

    <h2>Reset Your Password</h2>
    <form method="POST">
        <label>New Password (min 8 chars):</label><br>
        <input type="password" name="new_password" required><br><br>
        <input type="submit" value="Reset Password">
    </form>
    <p style="color:red;">{{ message }}</p>
</body>
</html>
"""

# Create verify form in html
verify_form = """
<!doctype html>
<html>
<head>
    <title>Verify Code</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
    <h2>Verify Email with Code</h2>
    <form method="POST">
        <label>Email:</label><br>
        <input type="text" name="email" required><br><br>

        <label>Verification Code:</label><br>
        <input type="text" name="code" required><br><br>

        <input type="submit" value="Verify">
    </form>
    <p style="color:red;">{{ message }}</p>
</body>
</html>
"""





# Login
@app.route("/", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        connection = sqlite3.connect("NEA.db")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]

            # Check for tasks due today or tomorrow
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)

            cursor.execute("SELECT title, due_date FROM tasks WHERE user_id=?", (user[0],))
            rows = cursor.fetchall()
            connection.close()

            due_soon = []
            for title, due_date in rows:
                try:
                    parsed_date = datetime.strptime(due_date, "%Y-%m-%d %H:%M").date()
                except ValueError:
                    parsed_date = datetime.strptime(due_date, "%Y-%m-%dT%H:%M").date()

                if parsed_date in [today, tomorrow]:
                    due_soon.append(title)

            # Store reminder in session
            session['due_soon'] = due_soon

            return redirect(url_for("home"))
        else:
            message = "Invalid email or password."
            connection.close()

    return render_template_string(login_form, message=message)



#Register account
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        security_code = request.form.get("security_code")

        if len(password) < 8:
            message = "Password must be at least 8 characters long."
        elif not security_code.isdigit():
            message = "Security code must be numeric."
        else:
            try:
                connection = sqlite3.connect("NEA.db")
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (email, password, security_code) VALUES (?, ?, ?)",
                               (email, password, security_code))
                connection.commit()
                connection.close()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                message = "Email already exists. Please choose another."

    return render_template_string(register_form, message=message)


#Verify identity
@app.route("/verify", methods=["GET", "POST"])
def verify_code():
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        code = request.form.get("code")
        connection = sqlite3.connect("NEA.db")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND security_code=?", (email, code))
        user = cursor.fetchone()
        connection.close()
        if user:
            user_email_temp["email"] = email
            return redirect(url_for("reset_password"))
        else:
            message = "Invalid email or security code."
    return render_template_string(verify_form, message=message)


#Reset password
@app.route("/reset", methods=["GET", "POST"])
def reset_password():
    message = ""
    if request.method == "POST":
        new_password = request.form.get("new_password")
        if len(new_password) < 8:
            message = "Password must be at least 8 characters long."
        else:
            email = user_email_temp.get("email")
            connection = sqlite3.connect("NEA.db")
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET password=? WHERE email=?", (new_password, email))
            connection.commit()
            connection.close()
            message = "Password reset successful."
            return redirect(url_for("login"))
    return render_template_string(reset_form, message=message)







#Task template
home_template = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Task Manager</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='home.css') }}">
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
        }
        .task {
            margin-bottom: 10px;
            padding: 10px;
            border: 1px solid #ccc;
        }
        #taskForm, #editForm {
            display: none;
            position: fixed;
            top: 20%;
            left: 35%;
            background: #fff;
            padding: 20px;
            border: 2px solid #333;
            z-index: 1001;
        }
        #overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
        }
    </style>
</head>
<body>
    <h2>Welcome, {{ user_email }}</h2>

    <header class="site-header">
        <nav class="navbar">
            <a href="/home">Home</a>
            <a href="/analysis">Analytics</a>
            <a href="/logout">Log Out</a>
            <a href="/Scheduling">Scheduling</a>
        </nav>
    </header>

    <h1>Task Manager</h1>
    <button onclick="showForm()">Add Task</button>

    <button onclick="toggleFilterForm()">Filter</button>

    <button onclick="showMessage()">Check Status</button>
    <p id="statusMessage" style="color:red; font-weight:bold;"></p>

    <div id="filterForm" style="display:none; margin-top:20px;">
        <form method="GET" action="/home">
            <label>Filter Word:</label><br>
            <input type="text" name="query" placeholder="Enter filter word"><br><br>

            <label>Search In:</label><br>
            <input type="checkbox" name="fields" value="title"> Title<br>
            <input type="checkbox" name="fields" value="description"> Description<br>
            <input type="checkbox" name="fields" value="due_date"> Due Date<br>
            <input type="checkbox" name="fields" value="label"> Label<br><br>

            <button type="submit">Apply Filter</button>
            <button type="button" onclick="toggleFilterForm()">Cancel</button>
        </form>
    </div>




    <div id="overlay" onclick="hideForm(); hideEditForm();"></div>
    <!-- Add Task Form -->
    <div id="taskForm">
        <form method="POST">
            <label>Title:</label><br>
            <input type="text" name="title" required><br><br>
            <label>Description:</label><br>
            <textarea name="description" required></textarea><br><br>
            <label>Due Date:</label><br>
            <input type="datetime-local" name="due_date" required><br><br>
            <label>Label:</label><br>
            <input type="text" name="label"><br><br>

            <label>Progress:</label><br>
            <input type="range" name="progress" min="0" max="100" value="0" step="10"
                   oninput="document.getElementById('progressOutput').value=this.value + '%'">
            <output id="progressOutput">0%</output><br><br>

            <button type="submit">Add Task</button>
            <button type="button" onclick="hideForm()">Cancel</button>
        </form>
    </div>

    <!-- Edit Task Form -->
    <div id="editForm">
        <form method="POST" action="/update_task">
            <input type="hidden" name="original_title" id="editOriginalTitle">
            <input type="hidden" name="original_due_date" id="editOriginalDueDate">

            <label>New Title:</label><br>
            <input type="text" name="title" required><br><br>

            <label>New Description:</label><br>
            <textarea name="description" required></textarea><br><br>

            <label>New Due Date:</label><br>
            <input type="datetime-local" name="due_date" required><br><br>

            <label>New Label:</label><br>
            <input type="text" name="label"><br><br>

            <label>Progress:</label><br>
            <!-- Notice: no oninput here -->
            <input type="range" name="progress" id="editProgress" min="0" max="100" step="10">
            <output id="editProgressOutput"></output><br><br>

            <button type="submit">Update Task</button>
            <button type="button" onclick="hideEditForm()">Cancel</button>
        </form>
    </div>



    <!-- Task Display -->
    {% for task in tasks %}
        <div class="task" style="position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{{ task.title }}</strong><br>
                    {{ task.description }}<br>
                    <em>Due: {{ task.due_date }}</em><br>
                    {% if task.label %}
                        <strong>Label:</strong> {{ task.label }}<br>
                    {% endif %}
                </div>
                <div style="text-align: right; min-width: 80px;">
                    <strong>{{ task.progress }}%</strong>
                </div>
            </div>
            <button onclick="openEditForm('{{ task.title }}', '{{ task.description }}', '{{ task.due_date }}', '{{ task.label }}')">Edit</button>
            <form method="POST" action="/delete_task" style="display:inline;">
                <input type="hidden" name="title" value="{{ task.title }}">
                <input type="hidden" name="due_date" value="{{ task.due_date }}">
                <button type="submit">Complete</button>
            </form>
        </div>
    {% endfor %}


    </body>
    <script>

    function showForm() {
    document.getElementById('taskForm').style.display = 'block';
    document.getElementById('overlay').style.display = 'block';
    }

    function hideForm() {
        document.getElementById('taskForm').style.display = 'none';
        document.getElementById('overlay').style.display = 'none';
    }

    function hideEditForm() {
        document.getElementById('editForm').style.display = 'none';
        document.getElementById('overlay').style.display = 'none';
    }

    function openEditForm(title, description, dueDate, label) {
        document.getElementById('editOriginalTitle').value = title;
        document.getElementById('editOriginalDueDate').value = dueDate;
        const editForm = document.getElementById('editForm');
        editForm.querySelector('input[name="title"]').value = title;
        editForm.querySelector('textarea[name="description"]').value = description;
        editForm.querySelector('input[name="due_date"]').value = dueDate.replace(' ', 'T');
        editForm.querySelector('input[name="label"]').value = label || "";
        editForm.style.display = 'block';
        document.getElementById('overlay').style.display = 'block';
    }



    function toggleFilterForm() {
        const form = document.getElementById("filterForm");
        form.style.display = form.style.display === "none" ? "block" : "none";
    }

    function showEditForm(task) {
        document.getElementById('editProgress').value = task.progress;
        document.getElementById('editProgressOutput').value = task.progress + '%';

        document.getElementById('editOriginalTitle').value = task.title;
        document.getElementById('editOriginalDueDate').value = task.due_date;


        document.getElementById('editForm').style.display = 'block';
    }

    function showMessage() {
        const msg = "{{ message }}";
        if (msg) {
            document.getElementById("statusMessage").innerText = msg;
        } else {
            document.getElementById("statusMessage").innerText = "No issues.";
        }
    }



    </script>




"""





# Editing Tasks
@app.route("/edit_task", methods=["POST"])
def edit_task(get_tasks, get_user_email):
    return render_template_string(home_template, tasks=get_tasks(), user_email=get_user_email(), show_edit_form=True, original_title=request.form["original_title"], original_due_date=request.form["original_due_date"])


# Updating (Live updating) Tasks
@app.route("/update_task", methods=["POST"])
def update_task():
    user_id = session.get("user_id")
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    original_title = request.form["original_title"]
    original_due_date = request.form["original_due_date"]
    new_title = request.form["title"]
    new_description = request.form["description"]
    new_due_date = datetime.strptime(request.form["due_date"], '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M')
    new_progress = int(request.form.get("progress", 0))
    new_label = request.form["label"]

    if new_progress == 100:
        # Move to completed_tasks
        cursor.execute("""
            INSERT INTO completed_tasks (user_id, title, description, due_date, label, progress, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, new_title, new_description, new_due_date, new_label, 100, datetime.now().strftime('%Y-%m-%d %H:%M')))

        cursor.execute("""
            DELETE FROM tasks WHERE user_id=? AND title=? AND due_date=?
        """, (user_id, original_title, original_due_date))
    else:
        # Just update in tasks
        cursor.execute("""
            UPDATE tasks SET title=?, description=?, due_date=?, label=?, progress=?
            WHERE user_id=? AND title=? AND due_date=?
        """, (new_title, new_description, new_due_date, new_label, new_progress,
              user_id, original_title, original_due_date))

    connection.commit()
    connection.close()
    return redirect(url_for("home"))



#Deleting/completeing
@app.route("/delete_task", methods=["POST"])
def delete_task():
    user_id = session.get("user_id")
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    title = request.form["title"]
    due_date = request.form["due_date"]

    # Fetch the task before deleting
    cursor.execute("""
        SELECT title, description, due_date, label, progress
        FROM tasks WHERE user_id=? AND title=? AND due_date=?
    """, (user_id, title, due_date))
    task = cursor.fetchone()

    if task:
        # Insert into completed_tasks
        cursor.execute("""
            INSERT INTO completed_tasks (user_id, title, description, due_date, label, progress, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, task[0], task[1], task[2], task[3], 100, datetime.now().strftime('%Y-%m-%d %H:%M')))

        # Delete from tasks
        cursor.execute("DELETE FROM tasks WHERE user_id=? AND title=? AND due_date=?", (user_id, title, due_date))

    connection.commit()
    connection.close()
    return redirect(url_for("home"))






# Home route

@app.route("/home", methods=["GET", "POST"])
def home():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    cursor.execute("SELECT email FROM users WHERE id=?", (user_id,))
    user_email = cursor.fetchone()[0].split("@")[0].title()

    message = ""  # default

    # Adding tasks
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        due_date_str = request.form["due_date"]
        label = request.form.get("label", "")
        progress = int(request.form.get("progress", 0))

        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            due_date_formatted = due_date.strftime('%Y-%m-%d %H:%M')
        except ValueError:
            due_date_formatted = "Invalid date"

        cursor.execute("""
            SELECT id FROM tasks WHERE user_id=? AND title=? AND due_date=?
        """, (user_id, title, due_date_formatted))
        existing_task = cursor.fetchone()

        if existing_task:
            connection.close()
            return render_template_string(
                home_template,
                tasks=[],
                user_email=user_email,
                message="Task with this title and due date already exists. Press Home to return."
                )
        else:
            cursor.execute("""
                INSERT INTO tasks (user_id, title, description, due_date, label, progress)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, title, description, due_date_formatted, label, progress))
            connection.commit()
            connection.close()
            return redirect(url_for("home"))


    # Fetch tasks
    cursor.execute("SELECT title, description, due_date, label, progress FROM tasks WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    connection.close()

    tasks = []
    due_soon = []
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    for row in rows:
        title, description, due_date, label, progress = row
        try:
            parsed_date = datetime.strptime(due_date, "%Y-%m-%d %H:%M").date()
        except ValueError:
            parsed_date = datetime.strptime(due_date, "%Y-%m-%dT%H:%M").date()

        tasks.append({
            'title': title,
            'description': description,
            'due_date': due_date,
            'label': label,
            'progress': progress
        })

        if parsed_date in [today, tomorrow]:
            due_soon.append(title)

    # If no duplicate message, but tasks are due soon
    if not message and due_soon:
        message = "Task due soon."

    return render_template_string(home_template, tasks=tasks, user_email=user_email, message=message)



# To test if the tasks are added correctly
@app.route("/completed")
def completed():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()
    cursor.execute("SELECT title, description, due_date, label, completed_at FROM completed_tasks WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    connection.close()

    completed_html = "<h2>Completed Tasks</h2>"
    for row in rows:
        completed_html += f"<div><strong>{row[0]}</strong> - {row[1]} (Due: {row[2]}, Completed: {row[4]})</div>"
    return completed_html





#Scheduling
scheduling_template = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Scheduling</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='calendar.css') }}">
</head>
<body>
    <header class="site-header">
        <nav class="navbar">
            <a href="/home">Home</a>
            <a href="/analysis">Analytics</a>
            <a href="/logout">Log Out</a>
            <a href="/Scheduling">Scheduling</a>
        </nav>
    </header>



    <h1>Calendar View - {{ now.strftime('%B %Y') }}</h1>

    <div style="margin-bottom: 20px;">
        <a href="/Scheduling?month={{ now.month - 1 if now.month > 1 else 12 }}&year={{ now.year if now.month > 1 else now.year - 1 }}">← Previous Month </a>
         |
        <a href="/Scheduling?month={{ now.month + 1 if now.month < 12 else 1 }}&year={{ now.year if now.month < 12 else now.year + 1 }}">Next Month →</a>
    </div>


    <div>
         {{ calendar_html|safe }}
    </div>

    <!-- Buttons to toggle forms -->
    <button onclick="toggleForm('eventForm')">Add Event</button>
    <button onclick="toggleForm('zoomForm')">Zoom into a Day</button>

    <!-- Add Event Form -->
    <div id="eventForm" style="display:none; margin-top:20px;">
        <form method="POST">
            <label>Title:</label><br>
            <input type="text" name="title" required><br><br>

            <label>Start Time:</label><br>
            <input type="datetime-local" name="start_time" required><br><br>

            <label>End Time:</label><br>
            <input type="datetime-local" name="end_time" required><br><br>

            <label>Description (optional):</label><br>
            <textarea name="description"></textarea><br><br>

            {% if message %}
                <p style="color:red;">{{ message }}</p>
                <label><input type="checkbox" name="confirm" value="yes" required> Confirm overlap and proceed</label><br><br>
            {% endif %}

            <input type="submit" value="Add Event">
        </form>
    </div>


    <!-- Zoom Form -->
    <div id="zoomForm" style="display:none;">
        <form method="GET" action="/Scheduling/day">
            <label>Select Day:</label><br>
            <input type="date" name="date" required><br><br>
            <input type="submit" value="View Day">
        </form>
    </div>

    <script>
        function toggleForm(id) {
            const el = document.getElementById(id);
            el.style.display = el.style.display === "none" ? "block" : "none";
        }

        {% if message %}
            toggleForm('eventForm');
        {% endif %}
    </script>

</body>
</html>
"""


# Over lapping
def has_overlap(cursor, user_id, new_start, new_end):
    cursor.execute("""
        SELECT title FROM events
        WHERE user_id=? AND (
            (start_time < ? AND end_time > ?) OR
            (start_time >= ? AND start_time < ?)
        )
    """, (user_id, new_end, new_start, new_start, new_end))
    overlapping_events = cursor.fetchall()

    cursor.execute("""
        SELECT title FROM tasks
        WHERE user_id=? AND (
            due_date BETWEEN ? AND ?
        )
    """, (user_id, new_start, new_end))
    overlapping_tasks = cursor.fetchall()

    return overlapping_events + overlapping_tasks









#Scheduling route

@app.route("/Scheduling", methods=["GET", "POST"])
def scheduling():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    year = int(request.args.get("year", datetime.now().year))
    month = int(request.args.get("month", datetime.now().month))
    now = datetime(year, month, 1)
    message = ""

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    cursor.execute("SELECT email FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    user_email = result[0].split("@")[0].title() if result else "Unknown"

    if request.method == "POST":
        title = request.form["title"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        description = request.form.get("description", "")
        confirm = request.form.get("confirm")

        overlaps = has_overlap(cursor, user_id, start_time, end_time)
        if overlaps and not confirm:
            overlap_titles = ", ".join([o[0] for o in overlaps])
            message = f"Overlaps with: {overlap_titles}. Resubmit to confirm."
        else:
            cursor.execute("""
                INSERT INTO events (user_id, title, description, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, title, description, start_time, end_time))
            connection.commit()

    # Fetch events and tasks
    cursor.execute("""
        SELECT title, start_time FROM events
        WHERE user_id=? AND strftime('%Y', start_time)=? AND strftime('%m', start_time)=?
    """, (user_id, str(year), f"{month:02d}"))
    events = cursor.fetchall()

    cursor.execute("""
        SELECT title, due_date FROM tasks
        WHERE user_id=? AND strftime('%Y', due_date)=? AND strftime('%m', due_date)=?
    """, (user_id, str(year), f"{month:02d}"))
    tasks = cursor.fetchall()
    connection.close()

    # Organize by day
    day_map = {}
    for title, start in events:
        try:
            parsed_date = datetime.strptime(start, "%Y-%m-%dT%H:%M")
        except ValueError:
            parsed_date = datetime.strptime(start, "%Y-%m-%d %H:%M")
        day = parsed_date.day

        day_map.setdefault(day, []).append(f"Event: {title}")

    for title, due_date in tasks:
        try:
            parsed_date = datetime.strptime(due_date, "%Y-%m-%dT%H:%M")
        except ValueError:
            parsed_date = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
        day = parsed_date.day

        day_map.setdefault(day, []).append(f"Task: {title}")

    cal = calendar.HTMLCalendar(calendar.MONDAY)
    calendar_html = cal.formatmonth(year, month)
    for day, items in day_map.items():
        item_list = "<br>".join(items)
        calendar_html = calendar_html.replace(f">{day}<", f">{day}<br><h5>{item_list}</h5><")

    return render_template_string(scheduling_template, calendar_html=calendar_html, user_email=user_email, now=now, message=message)



# Zoom into a day
@app.route("/Scheduling/day", methods=["GET"])
def view_day():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    date_str = request.args.get("date")
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    cursor.execute("SELECT title, description, due_date, label, id FROM tasks WHERE user_id=? AND date(due_date)=?", (user_id, date_str))
    tasks = cursor.fetchall()

    cursor.execute("SELECT title, description, start_time, end_time, id FROM events WHERE user_id=? AND date(start_time)=?", (user_id, date_str))
    events = cursor.fetchall()
    connection.close()

    sch_html = f"""
    <html>
        <body>
            <h2>Schedule for {date_str}</h2>
            <a href="/Scheduling">Back</a><br><br>

            <h3>Tasks</h3>
            {''.join([f"<div><strong>{t[0]}</strong>: {t[1]} ({t[2]})<form method='POST' action='/delete_task_day'><input type='hidden' name='id' value='{t[4]}'><input type='submit' value='Delete'></form></div>" for t in tasks]) or "No tasks"}

            <h3>Events</h3>
            {''.join([f"<div><strong>{e[0]}</strong>: {e[1]} ({e[2].replace('T', ' ')} to {e[3].replace('T', ' ')})<form method='POST' action='/delete_event_day'><input type='hidden' name='id' value='{e[4]}'><input type='submit' value='Delete'></form></div>" for e in events]) or "No events"}
        </body>
    </html>
    """
    return sch_html


@app.route("/delete_task_day", methods=["POST"])
def delete_task_day():
    task_id = request.form["id"]
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    connection.commit()
    connection.close()
    return redirect(request.referrer)

@app.route("/delete_event_day", methods=["POST"])
def delete_event_day():
    event_id = request.form["id"]
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM events WHERE id=?", (event_id,))
    connection.commit()
    connection.close()
    return redirect(request.referrer)








# Analytics template

analysis_template = """
<!doctype html>
<html>
<head>
    <title>Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="{{ url_for('static', filename='calendar.css') }}">
</head>
<body>

    <header class="site-header">
        <nav class="navbar">
            <a href="/home">Home</a>
            <a href="/analysis">Analytics</a>
            <a href="/logout">Log Out</a>
            <a href="/Scheduling">Scheduling</a>
        </nav>
    </header>



    <h2>Task Completion Analytics</h2>
    <p>Total tasks this month: {{ total }}</p>
    <p>Completed tasks: {{ completed }}</p>
    <p>Completion percentage: {{ percent|round(2) }}%</p>

    <canvas id="completionChart" style="width:350; height:350px;"></canvas>
    <script>
        const ctx = document.getElementById('completionChart').getContext('2d');
        const completionChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'Incomplete'],
                datasets: [{
                    data: [{{ completed }}, {{ total - completed }}],
                    backgroundColor: ['#4CAF50', '#FF5252']
                }]
            },
            options: {
                    responsive: false,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Tasks Completed This Month'
                        }
                    }
                }
        });
    </script>
</body>
</html>
"""


#  Anayltics route

@app.route("/analysis")
def analysis():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    # Get current month and year
    now = datetime.now()
    year = now.year
    month = now.month

    # Count tasks created this month
    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE user_id=? AND strftime('%Y', due_date)=? AND strftime('%m', due_date)=?
    """, (user_id, str(year), f"{month:02d}"))
    active_count = cursor.fetchone()[0]

    # Count completed tasks this month
    cursor.execute("""
        SELECT COUNT(*) FROM completed_tasks
        WHERE user_id=? AND strftime('%Y', completed_at)=? AND strftime('%m', completed_at)=?
    """, (user_id, str(year), f"{month:02d}"))
    completed_count = cursor.fetchone()[0]

    connection.close()

    total = active_count + completed_count
    percent_completed = (completed_count / total * 100) if total > 0 else 0

    return render_template_string(analysis_template,
                                  total=total,
                                  completed=completed_count,
                                  percent=percent_completed)








@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



if __name__ == "__main__":
    app.run(debug=True)


































'''
 |
 |
 |   Cycle 2:
 |
 | ->
 | ->
 | ->
 | ->






Add more text to explainations/objective and refceltions
Add comments (in word) to pictures to descibe what each image is
Add good example (about 10 ish (Berry said 5)) to the Evidence doc


'''







